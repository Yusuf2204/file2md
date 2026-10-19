import pytest
from app.parsers.base import ParserError
from app.parsers.json_parser import JsonParser
from pathlib import Path
from app.parsers.text import TextParser
from app.parsers.csv_parser import CsvParser


def test_text_parser_can_handle():
    parser = TextParser()
    assert parser.can_handle("notes.txt") is True
    assert parser.can_handle("README.md") is True
    assert parser.can_handle("document.pdf") is False


def test_text_parser_parse_utf8(tmp_path: Path):
    parser = TextParser()
    sample_file = tmp_path / "hello.txt"
    sample_file.write_text("Hello, File2MD!\nBaris kedua.", encoding="utf-8")

    result = parser.parse(sample_file)
    assert result.content == "Hello, File2MD!\nBaris kedua."
    assert result.metadata["encoding"] == "utf-8"
    assert result.metadata["line_count"] == 2
    assert len(result.warnings) == 0


def test_text_parser_parse_latin1(tmp_path: Path):
    parser = TextParser()
    sample_file = tmp_path / "iso.txt"
    # Tulis byte latin-1 (karakter 'é' dalam latin-1 adalah b'\xe9', bukan valid UTF-8)
    sample_file.write_bytes(b"Caf\xe9")

    result = parser.parse(sample_file)
    assert "Café" in result.content
    assert len(result.warnings) > 0

def test_json_parser_can_handle():
    parser = JsonParser()
    assert parser.can_handle("data.json") is True
    assert parser.can_handle("data.txt") is False

def test_json_parser_valid(tmp_path: Path):
    parser = JsonParser()
    sample = tmp_path / "valid.json"
    sample.write_text('{"name": "File2MD", "version": 1}', encoding="utf-8")
    result = parser.parse(sample)
    assert result.content.startswith("```json\n")
    assert result.content.endswith("\n```")
    assert '"name": "File2MD"' in result.content
    assert result.metadata["root_type"] == "dict"
    assert result.metadata["item_count"] == 2
    
def test_json_parser_invalid(tmp_path: Path):
    parser = JsonParser()
    sample = tmp_path / "invalid.json"
    sample.write_text('{"name": "File2MD", UNQUOTED}', encoding="utf-8")
    with pytest.raises(ParserError) as exc_info:
        parser.parse(sample)
    assert "Format JSON tidak valid" in str(exc_info.value)

def test_csv_parser_can_handle():
    parser = CsvParser()
    assert parser.can_handle("data.csv") is True
    assert parser.can_handle("data.tsv") is True
    assert parser.can_handle("data.json") is False

def test_csv_parser_valid(tmp_path: Path):
    parser = CsvParser()
    sample = tmp_path / "test.csv"
    sample.write_text("Nama,Usia,Kota\nBudi,25,Jakarta\nSiti,30,Surabaya\n", encoding="utf-8")
    result = parser.parse(sample)
    assert "| Nama | Usia | Kota |" in result.content
    assert "| --- | --- | --- |" in result.content
    assert "| Budi | 25 | Jakarta |" in result.content
    assert result.metadata["row_count"] == 3
    assert result.metadata["col_count"] == 3

def test_csv_parser_pipe_escaping(tmp_path: Path):
    parser = CsvParser()
    sample = tmp_path / "pipe.csv"
    sample.write_text('Produk,Deskripsi\nLaptop,"Model A | 16GB RAM"\n', encoding="utf-8")
    result = parser.parse(sample)
    # Memastikan pipe di dalam data di-escape agar tidak merusak tabel
    assert r"Model A \| 16GB RAM" in result.content
    
def test_csv_parser_semicolon_delimiter(tmp_path: Path):
    parser = CsvParser()
    sample = tmp_path / "semicolon.csv"
    sample.write_text("ID;Barang;Harga\n1;Buku;50000\n", encoding="utf-8")
    result = parser.parse(sample)
    assert result.metadata["delimiter"] == ";"
    assert "| ID | Barang | Harga |" in result.content