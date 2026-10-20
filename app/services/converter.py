import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import BinaryIO
from app.parsers.base import ParseResult, ParserError
from app.services.detector import FormatDetector, UnsupportedFormatError
from app.services.markdown_builder import BundleItem, MarkdownBuilder


@dataclass
class BundleOutput:
    markdown: str
    total_files: int
    success_files: int
    failed_files: int
    warnings: list[str]


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

    def convert_stream(
        self,
        file_obj: BinaryIO,
        filename: str,
        mime_type: str | None = None,
        max_file_size_bytes: int | None = None,
    ) -> ConversionOutput:
        """
        Menerima stream file, menyimpannya di file sementara yang aman (FR-11),
        memvalidasi ukuran sesuai kuota tier, melakukan parsing, dan menghapus file sementara.
        """
        max_limit = max_file_size_bytes or self.MAX_FILE_SIZE_BYTES
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)

        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=suffix)
        temp_path = Path(temp_file.name)

        try:
            # 1. Tulis ke file sementara dengan batas ukuran dinamis
            total_bytes = 0
            chunk_size = 64 * 1024  # 64 KB

            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_limit:
                    limit_mb = max_limit // (1024 * 1024)
                    raise ValueError(
                        f"Ukuran file '{filename}' melebihi batas tier Anda ({limit_mb} MB). "
                        f"Silakan login atau upgrade untuk batas lebih besar."
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

    def _describe_file(self, output: ConversionOutput) -> str:
        """Membuat ringkasan satu baris untuk Source Index."""
        meta = output.metadata
        parser = meta.get("parser", "")
        if parser == "ZipParser":
            total = meta.get("extracted_files", 0)
            return f"ZIP Archive ({total} files extracted)"
        if parser == "CodeParser":
            lang = meta.get("language", "code")
            lines = meta.get("line_count", 0)
            return f"{lang.title()} source ({lines} baris)"
        if parser == "PdfParser":
            pages = meta.get("page_count", 0)
            return f"PDF document ({pages} halaman)"
        if parser == "DocxParser":
            return "DOCX document"
        if parser == "XlsxParser":
            sheets = meta.get("total_sheets", 1)
            return f"Excel spreadsheet ({sheets} sheets)"
        if parser == "JsonParser":
            return "JSON data"
        if parser == "CsvParser":
            rows = meta.get("row_count", 0)
            return f"CSV table ({rows} baris)"
        return "Plain text"

    def bundle_streams(
        self,
        files: list[tuple[BinaryIO, str, str | None]],
        title: str = "Project Context",
        max_file_size_bytes: int | None = None,
    ) -> BundleOutput:
        """
        Mengonversi banyak file sekaligus dan menggabungkannya menjadi satu Markdown (FR-05).
        Mendukung laporan parsial: kegagalan satu file tidak membuat seluruh bundle gagal (Bab 14).
        """
        builder = MarkdownBuilder(title=title)
        items: list[BundleItem] = []
        all_warnings: list[str] = []
        success_count = 0
        failed_count = 0

        for file_obj, filename, mime_type in files:
            try:
                out = self.convert_stream(
                    file_obj=file_obj,
                    filename=filename,
                    mime_type=mime_type,
                    max_file_size_bytes=max_file_size_bytes,
                )
                desc = self._describe_file(out)
                items.append(BundleItem(
                    filename=filename,
                    content=out.markdown,
                    description=desc,
                    warnings=out.warnings,
                ))
                if out.warnings:
                    all_warnings.extend([f"[{filename}] {w}" for w in out.warnings])
                success_count += 1
            except Exception as exc:
                failed_count += 1
                err_msg = str(exc)
                items.append(BundleItem(
                    filename=filename,
                    error=err_msg,
                ))
                all_warnings.append(f"[{filename}] Gagal: {err_msg}")

        bundle_markdown = builder.build_bundle(items)

        return BundleOutput(
            markdown=bundle_markdown,
            total_files=len(files),
            success_files=success_count,
            failed_files=failed_count,
            warnings=all_warnings,
        )