import io
import shutil
from pathlib import Path
import pymupdf
from app.parsers.base import BaseParser, ParseResult, ParserError


class PdfParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".pdf"}

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type == "application/pdf":
            return True
        return False

    def _ocr_page(self, page: pymupdf.Page) -> str | None:
        """Ekstraksi teks dari halaman PDF scan menggunakan Tesseract OCR."""
        if not shutil.which("tesseract"):
            return None

        try:
            import pytesseract
            from PIL import Image

            # Render halaman PDF ke gambar dengan resolusi 150 DPI (optimal untuk OCR)
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            try:
                available_langs = pytesseract.get_languages()
            except Exception:
                available_langs = []

            lang = "eng"
            if "ind" in available_langs:
                lang = "ind+eng"

            text = pytesseract.image_to_string(img, lang=lang, config="--oem 1 --psm 3")
            return text.strip() if text else None
        except Exception:
            return None

    def parse(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []

        try:
            doc = pymupdf.open(file_path)
        except Exception as exc:
            raise ParserError(f"Gagal membuka file PDF: {str(exc)}") from exc

        page_count = len(doc)
        if page_count > 500:
            doc.close()
            raise ParserError(f"Dokumen PDF melebihi batas aman 500 halaman (ditemukan {page_count} halaman).")

        if page_count == 0:
            doc.close()
            return ParseResult(
                content="",
                metadata={"parser": "PdfParser", "page_count": 0},
                warnings=["Dokumen PDF tidak memiliki halaman."],
            )

        extracted_pages: list[str] = []
        empty_pages: int = 0
        ocr_pages_count: int = 0
        total_chars: int = 0

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()

            # Fallback otomatis ke OCR jika halaman tidak memiliki teks digital (scanned PDF)
            if not text:
                ocr_text = self._ocr_page(page)
                if ocr_text:
                    text = ocr_text
                    ocr_pages_count += 1

            if not text:
                empty_pages += 1
                continue

            total_chars += len(text)
            page_content = f"<!-- Page {page_num + 1} -->\n{text}"
            extracted_pages.append(page_content)

        doc.close()

        if ocr_pages_count > 0:
            warnings.append(
                f"{ocr_pages_count} dari {page_count} halaman diekstrak menggunakan OCR lokal (halaman berupa scan/gambar)."
            )

        if empty_pages == page_count:
            if shutil.which("tesseract"):
                warnings.append(
                    "Tidak ada teks yang dapat diekstrak meskipun OCR telah dijalankan (gambar mungkin buram atau kosong)."
                )
            else:
                warnings.append(
                    "Tidak ada teks yang dapat diekstrak. PDF berupa scan dokumen dan Tesseract OCR belum terpasang di sistem."
                )
        elif empty_pages > 0:
            warnings.append(
                f"{empty_pages} dari {page_count} halaman tidak mengandung teks (mungkin halaman kosong atau gambar tidak terbaca)."
            )

        markdown_output = "\n\n---\n\n".join(extracted_pages)

        return ParseResult(
            content=markdown_output,
            metadata={
                "parser": "PdfParser",
                "page_count": page_count,
                "text_pages": len(extracted_pages),
                "ocr_pages": ocr_pages_count,
                "char_count": total_chars,
            },
            warnings=warnings,
        )
