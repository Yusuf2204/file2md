import math
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance
from app.parsers.base import BaseParser, ParseResult, ParserError
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
        """Optimasi gambar: Grayscale, Upscaling, dan Kontras tinggi untuk Tesseract."""
        gray = img.convert("L")
        w, h = gray.size
        if w < 1000 or h < 1000:
            gray = gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Contrast(gray)
        return enhancer.enhance(2.0)

    def _run_ocr(self, img: Image.Image) -> str | None:
        """Jalankan OCR teroptimasi jika Tesseract tersedia di sistem."""
        if not shutil.which("tesseract"):
            return None
        try:
            import pytesseract
            # Cek bahasa yang terpasang di sistem
            available_langs = pytesseract.get_languages()
            lang = "eng"
            if "ind" in available_langs:
                lang = "eng+ind"  # Mengenali teks Indonesia & Inggris sekaligus

            processed = self._preprocess_for_ocr(img)
            # Flag: LSTM Neural Network (--oem 1) & Auto Page Segmentation (--psm 3)
            text = pytesseract.image_to_string(processed, lang=lang, config="--oem 1 --psm 3")
            return text.strip() if text else None
        except Exception:
            return None

    def parse(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []

        try:
            with Image.open(file_path) as img:
                vision_service = LocalVisionService.get_instance()
                ai_description = vision_service.describe_image(img)
                img_format = img.format or file_path.suffix.upper().replace(".", "")
                width, height = img.size
                mode = img.mode
                aspect_ratio = self._calc_aspect_ratio(width, height)
                file_size_bytes = file_path.stat().st_size
                formatted_size = self._format_size(file_size_bytes)

                # Jalankan OCR jika tersedia
                ocr_text = self._run_ocr(img)
        except Exception as exc:
            raise ParserError(f"Gagal membaca file gambar: {str(exc)}") from exc

        # Susun Tabel Metadata Markdown
        md_lines = [
            f"### Informasi Gambar: `{file_path.name}`\n",
            "| Atribut | Nilai |",
            "| --- | --- |",
            f"| **Format** | {img_format} |",
            f"| **Dimensi** | {width} × {height} px |",
            f"| **Rasio Aspek** | {aspect_ratio} |",
            f"| **Mode Warna** | {mode} |",
            f"| **Ukuran File** | {formatted_size} |",
        ]

        if ai_description:
            md_lines.extend([
                "\n---\n",
                "### Deskripsi Visual (Local AI Vision)\n",
                f"> **Konteks Gambar:** *\"{ai_description}\"*\n",
            ])

        # Tambahkan hasil OCR jika ada
        if ocr_text:
            md_lines.extend([
                "\n---\n",
                "### Ekstraksi Teks (OCR Lokal)\n",
                "> [!NOTE]\n",
                "> Teks diekstrak menggunakan OCR lokal (Tesseract dengan preprocessing) dan mungkin mengandung ketidakakuratan karakter.\n",
                f"```text\n{ocr_text}\n```",
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
            },
            warnings=warnings,
        )