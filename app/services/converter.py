import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import BinaryIO
from app.parsers.base import ParseResult, ParserError
from app.services.detector import FormatDetector, UnsupportedFormatError


@dataclass
class ConversionOutput:
    filename: str
    markdown: str
    metadata: dict
    warnings: list[str]


class ConversionService:
    # Batas ukuran default: 10 MB (FR-02)
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

    def __init__(self, detector: FormatDetector | None = None):
        self.detector = detector or FormatDetector()

    def convert_stream(self, file_obj: BinaryIO, filename: str, mime_type: str | None = None) -> ConversionOutput:
        """
        Menerima stream file, menyimpannya di file sementara yang aman (FR-11),
        memvalidasi ukuran, melakukan parsing, dan memastikan file sementara dihapus.
        """
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=suffix)
        temp_path = Path(temp_file.name)

        try:
            # 1. Tulis ke file sementara dengan batas ukuran (Resource limits FR-02)
            total_bytes = 0
            chunk_size = 64 * 1024  # 64 KB

            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > self.MAX_FILE_SIZE_BYTES:
                    raise ValueError(
                        f"Ukuran file '{filename}' melebihi batas maksimum {self.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                    )
                temp_file.write(chunk)

            temp_file.flush()
            temp_file.close()

            # 2. Dapatkan parser yang cocok
            parser = self.detector.get_parser(filename=filename, file_path=temp_path, mime_type=mime_type)

            # 3. Jalankan parsing
            result: ParseResult = parser.parse(temp_path)

            return ConversionOutput(
                filename=filename,
                markdown=result.content,
                metadata=result.metadata,
                warnings=result.warnings,
            )

        finally:
            # Cleanup selalu dieksekusi baik sukses maupun gagal (FR-11)
            if temp_path.exists():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass