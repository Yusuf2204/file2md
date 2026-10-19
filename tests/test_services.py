import io
from pathlib import Path
import pytest
from app.services.converter import ConversionService
from app.services.detector import UnsupportedFormatError


def test_converter_service_success():
    service = ConversionService()
    file_content = b"header1,header2\nval1,val2"
    file_obj = io.BytesIO(file_content)

    output = service.convert_stream(file_obj, filename="test.csv")
    assert "| header1 | header2 |" in output.markdown
    assert output.filename == "test.csv"
    assert output.metadata["row_count"] == 2

    # Verifikasi folder temp bersih (FR-11)
    temp_files = list(Path("temp").glob("*"))
    assert len(temp_files) == 0


def test_converter_service_unsupported():
    service = ConversionService()
    file_obj = io.BytesIO(b"binary data")

    with pytest.raises(UnsupportedFormatError):
        service.convert_stream(file_obj, filename="app.exe")


def test_converter_service_file_too_large():
    service = ConversionService()
    service.MAX_FILE_SIZE_BYTES = 100  # set batas kecil untuk test

    large_content = b"A" * 150
    file_obj = io.BytesIO(large_content)

    with pytest.raises(ValueError) as exc:
        service.convert_stream(file_obj, filename="big.txt")
    assert "melebihi batas" in str(exc.value)

    # Pastikan file temp tetap dibersihkan meskipun terjadi error
    temp_files = list(Path("temp").glob("*"))
    assert len(temp_files) == 0

def test_converter_service_bundle_success():
    service = ConversionService()
    files = [
        (io.BytesIO(b"print('hello')\n"), "main.py", "text/x-python"),
        (io.BytesIO(b"a,b\n1,2"), "data.csv", "text/csv"),
    ]

    output = service.bundle_streams(files, title="My Bundle")
    assert output.total_files == 2
    assert output.success_files == 2
    assert output.failed_files == 0
    assert "# My Bundle" in output.markdown
    assert "## Source Index" in output.markdown
    assert "- `main.py`" in output.markdown
    assert "- `data.csv`" in output.markdown
    assert "## File: main.py" in output.markdown
    assert "## File: data.csv" in output.markdown


def test_converter_service_bundle_partial_failure():
    service = ConversionService()
    files = [
        (io.BytesIO(b"Halo teks"), "catatan.txt", "text/plain"),
        (io.BytesIO(b"corrupt data"), "virus.exe", "application/octet-stream"),
    ]

    output = service.bundle_streams(files, title="Partial Bundle")
    assert output.total_files == 2
    assert output.success_files == 1
    assert output.failed_files == 1
    # Memastikan file yang gagal tercatat di indeks tanpa menghentikan bundle
    assert "- `virus.exe` — ❌ **Gagal:**" in output.markdown
    assert "## File: catatan.txt" in output.markdown