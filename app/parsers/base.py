from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParseResult:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class BaseParser(ABC):
    @abstractmethod
    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        """Menentukan apakah parser ini cocok untuk file yang diberikan."""
        pass

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """Mengekstrak dan mengonversi konten file menjadi ParseResult."""
        pass

class ParserError(Exception):
    """Exception untuk kegagalan saat parsing konten file."""
    pass