from app.services.presets import PresetService


def test_preset_chatgpt():
    content = "# Judul Dokumen\nIsi markdown."
    res = PresetService.apply_preset(content, "sample.md", "chatgpt")
    assert res == content


def test_preset_claude():
    content = "# Catatan Teknis"
    res = PresetService.apply_preset(content, "catatan.md", "claude")
    assert "<documents>" in res
    assert '<document index="1">' in res
    assert "<source>catatan.md</source>" in res
    assert "<document_content>\n# Catatan Teknis\n    </document_content>" in res
    assert "</documents>" in res


def test_preset_obsidian():
    content = "Ringkasan materi pembelajaran."
    res = PresetService.apply_preset(content, "materi_kuliah.pdf", "obsidian")
    assert "---" in res
    assert 'title: "Materi Kuliah"' in res
    assert 'source: "materi_kuliah.pdf"' in res
    assert "tags:" in res
    assert "Ringkasan materi pembelajaran." in res


def test_preset_html():
    content = "<h2>Subjudul</h2>"
    res = PresetService.apply_preset(content, "laporan.docx", "html")
    assert "<!DOCTYPE html>" in res
    assert "<title>Laporan</title>" in res
    assert "Sumber: laporan.docx" in res

