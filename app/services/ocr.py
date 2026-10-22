import logging
import math
import shutil
from dataclasses import dataclass
from typing import Optional
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    text: Optional[str]
    confidence: float
    line_count: int
    psm_mode: str
    is_dark_background: bool
    filtered_artifacts_count: int = 0


def levenshtein_distance(s1: list | str, s2: list | str) -> int:
    """Menghitung jarak Levenshtein antara dua sequence (karakter atau kata)."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Menghitung Character Error Rate (CER)."""
    ref_chars = list(reference)
    hyp_chars = list(hypothesis)
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    dist = levenshtein_distance(ref_chars, hyp_chars)
    return dist / len(ref_chars)


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Menghitung Word Error Rate (WER)."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return dist / len(ref_words)


class OCRService:
    """Layanan ekstraksi OCR adaptif dengan preprocessing cerdas dan noise filtering."""

    @staticmethod
    def preprocess_image(img: Image.Image) -> tuple[Image.Image, dict]:
        """Optimasi gambar untuk OCR: Deteksi mode gelap, inversi warna, autocontrast, dan border padding."""
        gray = img.convert("L")
        w, h = gray.size

        # 1. Analisis statistik intensitas untuk deteksi background gelap (console/terminal log)
        arr = np.array(gray)
        median_val = float(np.median(arr))
        mean_val = float(np.mean(arr))
        is_dark = median_val < 127 or mean_val < 120

        # 2. Inversi jika background gelap (Tesseract dilatih pada teks gelap di atas latar terang)
        processed = ImageOps.invert(gray) if is_dark else gray

        # 3. Normalisasi dynamic range dan kontras
        processed = ImageOps.autocontrast(processed, cutoff=2)
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(1.5)

        # 4. Upscaling adaptif (hanya jika resolusi teks terlalu kecil, hindari degradasi pada gambar lebar)
        if max(w, h) < 800:
            scale_factor = 2 if max(w, h) < 400 else 1.5
            processed = processed.resize(
                (int(w * scale_factor), int(h * scale_factor)),
                Image.Resampling.LANCZOS,
            )

        # 5. Tambahkan margin / border padding untuk mencegah artefak tepi dan clipping huruf terpotong
        padding = 25
        processed = ImageOps.expand(processed, border=padding, fill=255)

        info = {
            "is_dark_background": is_dark,
            "median_brightness": round(median_val, 1),
            "mean_brightness": round(mean_val, 1),
            "padding_applied": padding,
        }
        return processed, info

    @staticmethod
    def classify_image(img: Image.Image, ocr_text: Optional[str] = None) -> dict:
        """Heuristik klasifikasi tipe gambar untuk routing adaptif antara OCR dan Vision AI."""
        w, h = img.size
        aspect_ratio = (w / h) if h > 0 else 1.0

        # Cek statistik warna
        rgb = img.convert("RGB")
        arr = np.array(rgb)
        gray_arr = np.array(img.convert("L"))
        is_dark = float(np.median(gray_arr)) < 127

        # Cek variansi warna (foto memiliki saturasi dan variansi warna tinggi)
        color_std = float(np.std(arr, axis=(0, 1)).mean())

        # Indikator log / kode dalam teks
        text_lower = (ocr_text or "").lower()
        has_log_patterns = any(
            pat in text_lower
            for pat in [
                "warning", "error", "info", "debug", "rate limit",
                "production.", "exception", "failed", "status", "response",
                "{" , "}", "http", "curl", "agent", "user_agent"
            ]
        )
        has_timestamps = any(
            char.isdigit() for char in (ocr_text or "")
        ) and ("[" in text_lower or ":" in text_lower)

        # Tentukan tipe gambar
        if (aspect_ratio > 2.5 or aspect_ratio < 0.4) and (has_log_patterns or is_dark or has_timestamps):
            image_type = "LOG_OR_CODE"
            can_use_vision = False
            label = "Console / Log Screenshot"
        elif has_log_patterns and is_dark:
            image_type = "LOG_OR_CODE"
            can_use_vision = False
            label = "Terminal / Log Output"
        elif ocr_text and len(ocr_text.split()) > 30 and color_std < 35:
            image_type = "DOCUMENT"
            can_use_vision = False
            label = "Text Document / Scan"
        elif ocr_text and len(ocr_text.split()) > 10 and color_std >= 35:
            image_type = "UI_SCREENSHOT"
            can_use_vision = True
            label = "UI / Application Screenshot"
        else:
            image_type = "PHOTO_OR_ILLUSTRATION"
            can_use_vision = True
            label = "Photo / Graphic Illustration"

        return {
            "image_type": image_type,
            "label": label,
            "can_use_vision": can_use_vision,
            "aspect_ratio": round(aspect_ratio, 2),
            "color_std": round(color_std, 1),
            "is_dark": is_dark,
        }

    @classmethod
    def run_ocr(cls, img: Image.Image) -> OCRResult:
        """Menjalankan OCR menggunakan Tesseract dengan preprocessing cerdas dan pemfilteran artefak."""
        if not shutil.which("tesseract"):
            return OCRResult(
                text=None,
                confidence=0.0,
                line_count=0,
                psm_mode="N/A",
                is_dark_background=False,
            )

        try:
            import pytesseract

            processed, info = cls.preprocess_image(img)
            is_dark = info["is_dark_background"]

            # Pilih PSM adaptif: PSM 6 (single uniform block) untuk console log / wide aspect
            w, h = img.size
            aspect_ratio = (w / h) if h > 0 else 1.0
            psm = "6" if (aspect_ratio > 2.0 or aspect_ratio < 0.5 or is_dark) else "3"

            # Deteksi bahasa
            available_langs = pytesseract.get_languages()
            lang = "eng"
            if "ind" in available_langs:
                lang = "eng+ind"

            # Ambil structured OCR data beserta koordinat dan confidence
            data = pytesseract.image_to_data(
                processed,
                lang=lang,
                config=f"--oem 1 --psm {psm}",
                output_type=pytesseract.Output.DICT,
            )

            # Kelompokkan kata berdasarkan baris (block_num, par_num, line_num)
            lines: dict[tuple, list[tuple[str, int]]] = {}
            for i in range(len(data["text"])):
                word = data["text"][i].strip()
                conf = int(data["conf"][i])
                if conf == -1:
                    continue
                line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                lines.setdefault(line_key, []).append((word, conf))

            clean_lines = []
            line_confs = []
            filtered_artifacts = 0

            sorted_keys = sorted(lines.keys())
            for idx, line_key in enumerate(sorted_keys):
                items = lines[line_key]
                words = [t for t, c in items if t]
                if not words:
                    continue
                confs = [c for t, c in items if t]
                avg_conf = sum(confs) / len(confs)

                # Filter boundary noise:
                # 1. Baris terpotong di tepi atas atau bawah dengan confidence sangat rendah (< 35)
                is_boundary = (idx == 0 or idx == len(sorted_keys) - 1)
                if is_boundary and avg_conf < 35:
                    filtered_artifacts += 1
                    continue

                # 2. Karakter tunggal non-alfanumerik atau pecahan terpotong
                if len(words) == 1 and len(words[0]) <= 2 and avg_conf < 40:
                    filtered_artifacts += 1
                    continue

                clean_lines.append(" ".join(words))
                line_confs.append(avg_conf)

            final_text = "\n".join(clean_lines).strip() if clean_lines else None
            overall_conf = (sum(line_confs) / len(line_confs)) if line_confs else 0.0

            return OCRResult(
                text=final_text,
                confidence=round(overall_conf, 1),
                line_count=len(clean_lines),
                psm_mode=psm,
                is_dark_background=is_dark,
                filtered_artifacts_count=filtered_artifacts,
            )
        except Exception as exc:
            logger.warning(f"OCR execution failed: {exc}")
            return OCRResult(
                text=None,
                confidence=0.0,
                line_count=0,
                psm_mode="error",
                is_dark_background=False,
            )

