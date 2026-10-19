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

    def parse(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []

        try:
            doc = pymupdf.open(file_path)
        except Exception as exc:
            raise ParserError(f"Gagal membuka file PDF: {str(exc)}") from exc

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return ParseResult(
                content="",
                metadata={"parser": "PdfParser", "page_count": 0},
                warnings=["Dokumen PDF tidak memiliki halaman."],
            )

        extracted_pages: list[str] = []
        empty_pages: int = 0
        total_chars: int = 0

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()

            if not text:
                empty_pages += 1
                continue

            total_chars += len(text)
            page_content = f"<!-- Page {page_num + 1} -->\n{text}"
            extracted_pages.append(page_content)

        doc.close()

        if empty_pages == page_count:
            warnings.append(
                "Tidak ada teks yang dapat diekstrak. PDF mungkin berupa gambar/scan dokumen (membutuhkan OCR)."
            )
        elif empty_pages > 0:
            warnings.append(
                f"{empty_pages} dari {page_count} halaman tidak mengandung teks (mungkin halaman kosong atau gambar)."
            )

        markdown_output = "\n\n---\n\n".join(extracted_pages)

        return ParseResult(
            content=markdown_output,
            metadata={
                "parser": "PdfParser",
                "page_count": page_count,
                "text_pages": len(extracted_pages),
                "char_count": total_chars,
            },
            warnings=warnings,
        )