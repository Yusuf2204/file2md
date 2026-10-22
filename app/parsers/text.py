from pathlib import Path
import chardet
from app.parsers.base import BaseParser, ParseResult, ParserError


class TextParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type and mime_type.startswith("text/"):
            return True
        return False

    def parse(self, file_path: Path) -> ParseResult:
        raw_bytes = file_path.read_bytes()
        warnings: list[str] = []

        # Cegah file binary masquerading sebagai text (misal: executable atau binary dumps)
        if b"\x00" in raw_bytes[:8192]:
            raise ParserError("File terdeteksi sebagai binary yang mengandung null bytes, bukan teks murni.")

        try:
            content = raw_bytes.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            # Deteksi encoding menggunakan chardet bawaan sistem
            detected = chardet.detect(raw_bytes)
            encoding = detected.get("encoding") or "latin-1"
            content = raw_bytes.decode(encoding, errors="replace")
            warnings.append(f"File dibaca menggunakan fallback encoding '{encoding}'.")

        # Normalisasi akhir baris (CRLF -> LF)
        normalized_content = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized_content.split("\n")

        return ParseResult(
            content=normalized_content,
            metadata={
                "parser": "TextParser",
                "encoding": encoding,
                "line_count": len(lines),
                "char_count": len(normalized_content),
            },
            warnings=warnings,
        )