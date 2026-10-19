import zipfile
from pathlib import Path
from app.parsers.zip_parser import ZipParser


def test_zip_parser_can_handle():
    parser = ZipParser()
    assert parser.can_handle("project.zip")
    assert parser.can_handle("backup.ZIP")
    assert parser.can_handle("archive", mime_type="application/zip")
    assert not parser.can_handle("document.pdf")


def test_zip_parser_extracts_and_bundles(tmp_path: Path):
    zip_path = tmp_path / "test_repo.zip"

    # Buat file zip dummy berisi file kode dan teks
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("README.md", "# Judul Repo\nDokumentasi proyek.")
        zf.writestr("src/main.py", "def hello():\n    print('Hello World')\n")
        # File junk yang harus diabaikan
        zf.writestr(".git/HEAD", "ref: refs/heads/main")
        zf.writestr("node_modules/dummy.js", "console.log('ignore')")

    parser = ZipParser()
    result = parser.parse(zip_path)

    # Verifikasi hasil
    assert result.metadata["extracted_files"] == 2
    assert "README.md" in result.content
    assert "src/main.py" in result.content
    assert ".git/HEAD" not in result.content
    assert "node_modules" not in result.content
    assert "Source Index" in result.content