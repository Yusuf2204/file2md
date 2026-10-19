import json
from pathlib import Path
import chardet
from app.parsers.base import BaseParser, ParseResult, ParserError


class JsonParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".json"}

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type == "application/json":
            return True
        return False

    def parse(self, file_path: Path) -> ParseResult:
        raw_bytes = file_path.read_bytes()
        warnings: list[str] = []

        # 1. Decode text
        try:
            content_str = raw_bytes.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            detected = chardet.detect(raw_bytes)
            encoding = detected.get("encoding") or "latin-1"
            content_str = raw_bytes.decode(encoding, errors="replace")
            warnings.append(f"JSON dibaca dengan encoding '{encoding}'.")

        # 2. Parse & Validasi JSON
        try:
            parsed_data = json.loads(content_str)
        except json.JSONDecodeError as exc:
            raise ParserError(
                f"Format JSON tidak valid pada baris {exc.lineno}, kolom {exc.colno}: {exc.msg}"
            ) from exc

        # 3. Format Pretty JSON
        formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)

        # 4. Format Markdown block
        markdown_output = f"```json\n{formatted_json}\n```"

        # Hitung statistik metadata
        root_type = type(parsed_data).__name__
        item_count = len(parsed_data) if isinstance(parsed_data, (dict, list)) else 1

        return ParseResult(
            content=markdown_output,
            metadata={
                "parser": "JsonParser",
                "encoding": encoding,
                "root_type": root_type,
                "item_count": item_count,
            },
            warnings=warnings,
        )