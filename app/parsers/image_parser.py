import math
import shutil
from pathlib import Path
from PIL import Image
# Batasi dekompresi gambar untuk mencegah DoS / Decompression Bomb
Image.MAX_IMAGE_PIXELS = 50_000_000
from app.parsers.base import BaseParser, ParseResult, ParserError
from app.services.ocr import OCRService
from app.services.vision import LocalVisionService


class ImageParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    SUPPORTED_MIMES = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/bmp",
        "image/gif",
    }

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type in self.SUPPORTED_MIMES:
            return True
        return False

    def _calc_aspect_ratio(self, width: int, height: int) -> str:
        if height == 0:
            return "N/A"
        gcd = math.gcd(width, height)
        w_ratio = width // gcd
        h_ratio = height // gcd
        if w_ratio < 50 and h_ratio < 50:
            return f"{w_ratio}:{h_ratio}"
        return f"{width / height:.2f}:1"

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.2f} MB"

    def _preprocess_for_ocr(self, img: Image.Image) -> Image.Image:
        """Optimasi gambar: Grayscale, Inversi mode gelap, Upscaling adaptif, dan Kontras tinggi."""
        processed, _ = OCRService.preprocess_image(img)
        return processed

    def _run_ocr(self, img: Image.Image) -> str | None:
        """Jalankan OCR teroptimasi jika Tesseract tersedia di sistem."""
        result = OCRService.run_ocr(img)
        return result.text

    def parse(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []

        try:
            with Image.open(file_path) as img:
                img_format = img.format or file_path.suffix.upper().replace(".", "")
                width, height = img.size
                mode = img.mode
                aspect_ratio = self._calc_aspect_ratio(width, height)
                file_size_bytes = file_path.stat().st_size
                formatted_size = self._format_size(file_size_bytes)

                # 1. Jalankan OCR adaptif
                ocr_result = OCRService.run_ocr(img)
                ocr_text = ocr_result.text

                # 2. Klasifikasi tipe gambar untuk routing adaptif
                classification = OCRService.classify_image(img, ocr_text)

                # 3. Jalankan vision AI secara adaptif (hanya jika sesuai dan tidak menimbulkan konflik)
                ai_description = None
                if classification["can_use_vision"]:
                    vision_service = LocalVisionService.get_instance()
                    ai_description = vision_service.describe_image(img)
                    # Resolusi konflik: jika vision menghasilkan halusinasi fotografi pada log/kode, abaikan
                    if ai_description and classification["image_type"] == "LOG_OR_CODE":
                        ai_description = None

        except Exception as exc:
            raise ParserError(f"Gagal membaca file gambar: {str(exc)}") from exc

        # Susun Konten Markdown Ringkas & Token-Efficient (Zero Base64 Bloat)
        md_lines = [
            f"### Informasi Gambar: `{file_path.name}`\n",
            f"![{file_path.name}]({file_path.name})\n",
            "| Atribut | Nilai |",
            "| --- | --- |",
            f"| **Format** | {img_format} |",
            f"| **Dimensi** | {width} × {height} px |",
            f"| **Rasio Aspek** | {aspect_ratio} |",
            f"| **Mode Warna** | {mode} |",
            f"| **Ukuran File** | {formatted_size} |",
            f"| **Tipe Konten** | {classification['label']} |",
        ]

        if ai_description:
            md_lines.extend([
                "\n---\n",
                "### Deskripsi Visual (Local AI Vision)\n",
                f"> **Konteks Gambar:** *\"{ai_description}\"*\n",
            ])

        # Tambahkan hasil OCR jika ada
        if ocr_text:
            code_lang = "log" if classification["image_type"] == "LOG_OR_CODE" else "text"
            md_lines.extend([
                "\n---\n",
                "### Ekstraksi Teks (OCR Lokal)\n",
                "> [!NOTE]\n",
                "> Teks diekstrak menggunakan OCR lokal (Tesseract dengan preprocessing) dan mungkin mengandung ketidakakuratan karakter.\n",
                f"```{code_lang}\n{ocr_text}\n```",
            ])
        else:
            if not shutil.which("tesseract"):
                warnings.append(
                    "OCR lokal tidak aktif karena binary 'tesseract' belum terpasang di sistem. Hanya metadata gambar yang diekstrak."
                )

        return ParseResult(
            content="\n".join(md_lines),
            metadata={
                "parser": "ImageParser",
                "format": img_format,
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "mode": mode,
                "file_size": formatted_size,
                "ai_caption": ai_description or "N/A",
                "has_ocr_text": bool(ocr_text),
                "image_type": classification["image_type"],
                "content_label": classification["label"],
                "ocr_confidence": ocr_result.confidence,
                "ocr_lines": ocr_result.line_count,
                "is_dark_background": ocr_result.is_dark_background,
            },
            warnings=warnings,
        )
