from pathlib import Path
import chardet
from app.parsers.base import BaseParser, ParseResult


class CodeParser(BaseParser):
    EXTENSION_LANG_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".xml": "xml",
        ".php": "php",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".java": "java",
        ".rb": "ruby",
        ".lua": "lua",
        ".ini": "ini",
        ".env": "bash",
        ".dockerfile": "dockerfile",
    }

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.EXTENSION_LANG_MAP:
            return True
        if filename.lower() in {"dockerfile", "makefile", ".env"}:
            return True
        return False

    def _determine_language(self, filename: str) -> str:
        name_lower = filename.lower()
        if name_lower == "dockerfile":
            return "dockerfile"
        if name_lower == "makefile":
            return "makefile"
        ext = Path(filename).suffix.lower()
        return self.EXTENSION_LANG_MAP.get(ext, "")

    def _safe_code_fence(self, content: str) -> str:
        """Menghindari broken markdown jika code berisi triple backticks (PRD Bab 10)."""
        fence = "```"
        while fence in content:
            fence += "`"
        return fence

    def parse(self, file_path: Path) -> ParseResult:
        raw_bytes = file_path.read_bytes()
        warnings: list[str] = []

        try:
            content = raw_bytes.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            detected = chardet.detect(raw_bytes)
            encoding = detected.get("encoding") or "latin-1"
            content = raw_bytes.decode(encoding, errors="replace")
            warnings.append(f"Source code dibaca dengan encoding '{encoding}'.")

        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        lang = self._determine_language(file_path.name)
        fence = self._safe_code_fence(normalized)

        markdown = f"{fence}{lang}\n{normalized}\n{fence}"
        lines = normalized.split("\n")

        return ParseResult(
            content=markdown,
            metadata={
                "parser": "CodeParser",
                "language": lang,
                "encoding": encoding,
                "line_count": len(lines),
                "char_count": len(normalized),
            },
            warnings=warnings,
        )