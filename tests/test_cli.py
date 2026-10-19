import sys
from pathlib import Path
from app.cli import main


def test_cli_convert_to_stdout(tmp_path: Path, monkeypatch, capsys):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Halo dari CLI!", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["file2md", "convert", str(test_file)])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    assert "Halo dari CLI!" in captured.out


def test_cli_convert_to_file(tmp_path: Path, monkeypatch, capsys):
    test_file = tmp_path / "data.json"
    test_file.write_text('{"name": "File2MD"}', encoding="utf-8")
    out_file = tmp_path / "output.md"

    monkeypatch.setattr(
        sys, "argv", ["file2md", "convert", str(test_file), "-o", str(out_file)]
    )

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "File2MD" in content

    captured = capsys.readouterr()
    assert "Berhasil" in captured.err  # Status log harus masuk ke stderr


def test_cli_bundle(tmp_path: Path, monkeypatch):
    f1 = tmp_path / "a.txt"
    f1.write_text("Isi File A", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("Isi File B", encoding="utf-8")
    out_file = tmp_path / "bundle.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "file2md",
            "bundle",
            str(f1),
            str(f2),
            "-o",
            str(out_file),
            "--title",
            "Test Bundle CLI",
        ],
    )

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "Test Bundle CLI" in content
    assert "Isi File A" in content
    assert "Isi File B" in content


def test_cli_file_not_found(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["file2md", "convert", "tidak_ada_xyz.txt"])

    try:
        main()
    except SystemExit as e:
        assert e.code == 1

    captured = capsys.readouterr()
    assert "tidak ditemukan" in captured.err