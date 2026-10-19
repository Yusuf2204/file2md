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