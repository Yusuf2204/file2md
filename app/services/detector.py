from pathlib import Path
import filetype
from app.parsers.base import BaseParser
from app.parsers.text import TextParser
from app.parsers.json_parser import JsonParser
from app.parsers.csv_parser import CsvParser
from app.parsers.code import CodeParser
from app.parsers.pdf import PdfParser
from app.parsers.docx import DocxParser
from app.parsers.xlsx import XlsxParser
from app.parsers.image_parser import ImageParser
from app.parsers.zip_parser import ZipParser

class UnsupportedFormatError(Exception):
    """Exception ketika format file tidak didukung."""
    pass

class FormatDetector:
    def __init__(self, parsers: list[BaseParser] | None = None):
        self.parsers: list[BaseParser] = parsers or [
            JsonParser(),
            CsvParser(),
            XlsxParser(),
            CodeParser(),
            PdfParser(),
            DocxParser(),
            ImageParser(),
            ZipParser(), 
            TextParser(),
        ]

    def detect_mime(self, file_path: Path) -> str | None:
        """Deteksi MIME type menggunakan header byte (magic numbers)."""
        kind = filetype.guess(file_path)
        if kind:
            return kind.mime
        return None

    def get_parser(self, filename: str, file_path: Path | None = None, mime_type: str | None = None) -> BaseParser:
        # Jika file_path ada dan mime_type belum diberikan, coba tebak dari magic bytes
        if file_path and not mime_type:
            mime_type = self.detect_mime(file_path)

        for parser in self.parsers:
            if parser.can_handle(filename, mime_type=mime_type):
                return parser

        ext = Path(filename).suffix.lower() or "tanpa ekstensi"
        raise UnsupportedFormatError(
            f"Format file '{ext}' untuk '{filename}' belum didukung saat ini."
        )