import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from app.parsers.base import BaseParser, ParseResult, ParserError
from app.services.markdown_builder import BundleItem, MarkdownBuilder


class ZipParser(BaseParser):
    SUPPORTED_EXTENSIONS = {".zip"}
    SUPPORTED_MIME_TYPES = {
        "application/zip",
        "application/x-zip-compressed",
        "multipart/x-zip",
    }

    # Folder / file yang otomatis diabaikan agar tidak mencemari context LLM
    IGNORE_PATTERNS = {
        "__macosx",
        ".ds_store",
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "__pycache__",
        ".pytest_cache",
    }

    # Batas keamanan (Security limits)
    MAX_TOTAL_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
    MAX_FILES_COUNT = 100

    def can_handle(self, filename: str, mime_type: str | None = None) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if mime_type and mime_type.lower() in self.SUPPORTED_MIME_TYPES:
            return True
        return False

    def _should_ignore(self, path_str: str) -> bool:
        parts = Path(path_str).parts
        for part in parts:
            if part.lower() in self.IGNORE_PATTERNS:
                return True
            if part.startswith(".") and part != ".":
                return True
        return False

    def parse(self, file_path: Path) -> ParseResult:
        if not zipfile.is_zipfile(file_path):
            raise ParserError("File bukan merupakan arsip ZIP yang valid atau rusak.")

        extract_dir = Path(tempfile.mkdtemp(prefix="zip_extract_"))
        warnings: list[str] = []
        items: list[BundleItem] = []

        try:
            # Lazy import FormatDetector untuk mencegah circular import
            from app.services.detector import FormatDetector, UnsupportedFormatError
            detector = FormatDetector()

            with zipfile.ZipFile(file_path, "r") as zf:
                infolist = zf.infolist()
                total_uncompressed = sum(info.file_size for info in infolist)

                if total_uncompressed > self.MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise ParserError(
                        f"Total ukuran uncompressed ZIP ({total_uncompressed // (1024*1024)} MB) "
                        f"melebihi batas aman {self.MAX_TOTAL_UNCOMPRESSED_BYTES // (1024*1024)} MB."
                    )

                extracted_count = 0
                for info in infolist:
                    # 1. Lewati folder
                    if info.is_dir():
                        continue

                    # 2. Keamanan: Cegah directory traversal (Zip Slip vulnerability)
                    if ".." in info.filename or info.filename.startswith(("/", "\\")):
                        warnings.append(f"Dilewati karena path mencurigakan: {info.filename}")
                        continue

                    # 3. Lewati file junk / binary compiler / node_modules
                    if self._should_ignore(info.filename):
                        continue

                    if extracted_count >= self.MAX_FILES_COUNT:
                        warnings.append(f"Mencapai batas maksimum {self.MAX_FILES_COUNT} file. Sisa file diabaikan.")
                        break

                    # 4. Ekstrak satu per satu ke folder sementara
                    target_file = extract_dir / info.filename
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target_file, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                    # 5. Cari parser yang cocok
                    try:
                        parser = detector.get_parser(filename=info.filename, file_path=target_file)
                        # Hindari recursive zip extraction di dalam zip
                        if isinstance(parser, ZipParser):
                            continue

                        result = parser.parse(target_file)
                        items.append(
                            BundleItem(
                                filename=info.filename,
                                content=result.content,
                                description=f"{result.metadata.get('parser', 'Parser')} ({info.file_size} bytes)",
                                warnings=result.warnings,
                            )
                        )
                        extracted_count += 1
                    except UnsupportedFormatError:
                        # Lewati file binary/tidak didukung tanpa membuat zip error total
                        continue
                    except Exception as e:
                        items.append(
                            BundleItem(
                                filename=info.filename,
                                error=str(e),
                            )
                        )
                        warnings.append(f"Gagal memproses {info.filename}: {e}")

            if not items:
                return ParseResult(
                    content="*Arsip ZIP tidak berisi file yang didukung atau semua file diabaikan.*",
                    metadata={"parser": "ZipParser", "extracted_files": 0},
                    warnings=warnings or ["Tidak ada file yang dapat diproses dari arsip ZIP ini."],
                )

            # Buat bundel dokumen Markdown
            builder = MarkdownBuilder(title=f"ZIP Bundle: {file_path.name}")
            bundle_markdown = builder.build_bundle(items)

            return ParseResult(
                content=bundle_markdown,
                metadata={"parser": "ZipParser", "extracted_files": len(items)},
                warnings=warnings,
            )

        except Exception as exc:
            if isinstance(exc, ParserError):
                raise
            raise ParserError(f"Gagal membaca arsip ZIP: {exc}")
        finally:
            # Pastikan folder ekstraksi sementara selalu dihapus bersih
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)