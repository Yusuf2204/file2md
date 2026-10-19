import csv
import io
from pathlib import Path
import chardet
from app.parsers.base import BaseParser, ParseResult, ParserError


class CsvParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".csv", ".tsv"}

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type in {"text/csv", "text/tab-separated-values"}:
            return True
        return False

    def _sanitize_cell(self, cell: str) -> str:
        """Escape karakter pipe dan ubah newline dalam sel agar tidak merusak tabel Markdown."""
        clean = str(cell).strip()
        # Escape pipe
        clean = clean.replace("|", "\\|")
        # Ganti newline dalam sel dengan spasi atau <br>
        clean = clean.replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")
        return clean

    def parse(self, file_path: Path) -> ParseResult:
        raw_bytes = file_path.read_bytes()
        warnings: list[str] = []

        # 1. Decode bytes ke string
        try:
            content_str = raw_bytes.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            detected = chardet.detect(raw_bytes)
            encoding = detected.get("encoding") or "latin-1"
            content_str = raw_bytes.decode(encoding, errors="replace")
            warnings.append(f"CSV dibaca menggunakan fallback encoding '{encoding}'.")

        if not content_str.strip():
            return ParseResult(
                content="",
                metadata={"parser": "CsvParser", "row_count": 0, "col_count": 0},
                warnings=["File CSV kosong."],
            )

        # 2. Deteksi delimiter
        delimiter = ","
        if file_path.suffix.lower() == ".tsv":
            delimiter = "\t"
        else:
            try:
                sample = content_str[:2048]
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ","

        # 3. Baca data baris per baris
        reader = csv.reader(io.StringIO(content_str), delimiter=delimiter)
        rows: list[list[str]] = [row for row in reader if any(cell.strip() for cell in row)]

        if not rows:
            return ParseResult(
                content="",
                metadata={"parser": "CsvParser", "row_count": 0, "col_count": 0},
                warnings=["File CSV tidak memiliki data yang valid."],
            )

        header = rows[0]
        data_rows = rows[1:]
        col_count = len(header)

        # 4. Susun Tabel Markdown
        clean_headers = [self._sanitize_cell(col) or f"Col_{i+1}" for i, col in enumerate(header)]
        separator = ["---"] * col_count

        md_lines: list[str] = [
            "| " + " | ".join(clean_headers) + " |",
            "| " + " | ".join(separator) + " |",
        ]

        for row in data_rows:
            # Pad kolom jika baris ini lebih pendek dari header
            if len(row) < col_count:
                row = row + [""] * (col_count - len(row))
            clean_cells = [self._sanitize_cell(cell) for cell in row[:col_count]]
            md_lines.append("| " + " | ".join(clean_cells) + " |")

        markdown_table = "\n".join(md_lines)

        return ParseResult(
            content=markdown_table,
            metadata={
                "parser": "CsvParser",
                "encoding": encoding,
                "delimiter": delimiter,
                "row_count": len(rows),
                "col_count": col_count,
            },
            warnings=warnings,
        )