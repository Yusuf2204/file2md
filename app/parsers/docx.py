from pathlib import Path
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from app.parsers.base import BaseParser, ParseResult, ParserError


class DocxParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".docx"}

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return True
        return False

    def _sanitize_cell(self, text: str) -> str:
        clean = text.strip().replace("|", r"\|")
        clean = clean.replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")
        return clean

    def _convert_table(self, table: Table) -> str:
        if not table.rows:
            return ""

        headers = [self._sanitize_cell(cell.text) or f"Col_{i+1}" for i, cell in enumerate(table.rows[0].cells)]
        col_count = len(headers)
        separator = ["---"] * col_count

        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |",
        ]

        for row in table.rows[1:]:
            cells = [self._sanitize_cell(cell.text) for cell in row.cells[:col_count]]
            if len(cells) < col_count:
                cells += [""] * (col_count - len(cells))
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    def _convert_paragraph(self, p: Paragraph) -> str | None:
        text = p.text.strip()
        if not text:
            return None

        style_name = (p.style.name if p.style else "").lower()

        if "heading 1" in style_name:
            return f"# {text}"
        if "heading 2" in style_name:
            return f"## {text}"
        if "heading 3" in style_name:
            return f"### {text}"
        if "heading 4" in style_name:
            return f"#### {text}"
        if "bullet" in style_name:
            return f"- {text}"
        if "number" in style_name:
            return f"1. {text}"

        return text

    def parse(self, file_path: Path) -> ParseResult:
        warnings: list[str] = []

        try:
            doc = docx.Document(file_path)
        except Exception as exc:
            raise ParserError(f"Gagal membaca file DOCX: {str(exc)}") from exc

        md_parts: list[str] = []
        para_count = 0
        table_count = 0

        # Iterasi body secara urut agar paragraf dan tabel tidak tertukar posisi
        for child in doc.element.body:
            tag = child.tag.split("}")[-1]

            if tag == "p":
                p = Paragraph(child, doc)
                para_md = self._convert_paragraph(p)
                if para_md:
                    md_parts.append(para_md)
                    para_count += 1

            elif tag == "tbl":
                table = Table(child, doc)
                tbl_md = self._convert_table(table)
                if tbl_md:
                    md_parts.append(tbl_md)
                    table_count += 1

        if not md_parts:
            warnings.append("Dokumen DOCX kosong atau tidak memiliki teks yang terbaca.")

        markdown_output = "\n\n".join(md_parts)

        return ParseResult(
            content=markdown_output,
            metadata={
                "parser": "DocxParser",
                "paragraph_count": para_count,
                "table_count": table_count,
                "char_count": len(markdown_output),
            },
            warnings=warnings,
        )