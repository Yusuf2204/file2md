import shutil
from pathlib import Path
import pytest
from PIL import Image, ImageDraw, ImageFont
from app.parsers.image_parser import ImageParser
from app.services.ocr import OCRService, calculate_cer, calculate_wer


@pytest.fixture
def parser():
    return ImageParser()


def _get_font(size: int = 20) -> ImageFont.ImageFont:
    """Mengambil font TTF sistem untuk fixture uji, atau fallback ke default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in font_paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def test_cer_wer_calculation():
    """Memverifikasi fungsi penghitungan metrik CER dan WER."""
    ref = "2026-10-08 10:26:24 production.WARNING Rate Limit"
    hyp_exact = "2026-10-08 10:26:24 production.WARNING Rate Limit"
    assert calculate_cer(ref, hyp_exact) == 0.0
    assert calculate_wer(ref, hyp_exact) == 0.0

    # Satu token terpisah (production.WARNING menjadi production WARNING)
    hyp_1diff = "2026-10-08 10:26:24 production WARNING Rate Limit"
    cer = calculate_cer(ref, hyp_1diff)
    assert 0.0 < cer < 0.05
    wer = calculate_wer(ref, hyp_1diff)
    assert 0.0 < wer <= 0.40


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract belum terpasang di sistem")
def test_case_test_ocr_jpeg_real_fixture(parser):
    """Pengujian studi kasus nyata: docs/test/test_ocr.jpeg."""
    img_path = Path("docs/test/test_ocr.jpeg")
    if not img_path.exists():
        pytest.skip("File docs/test/test_ocr.jpeg tidak ditemukan")

    result = parser.parse(img_path)

    # 1. OCR-001: Verifikasi tidak ada halusinasi fotografi pada log screenshot
    assert result.metadata["ai_caption"] in [None, "N/A"]
    assert "woman in a black dress" not in result.content.lower()

    # 2. OCR-003: Verifikasi klasifikasi adaptif
    assert result.metadata["image_type"] == "LOG_OR_CODE"
    assert result.metadata["is_dark_background"] is True
    assert result.metadata["has_ocr_text"] is True

    # 3. OCR-002: Verifikasi 9 log lines utuh dan timestamp terpelihara
    content = result.content
    assert "```log" in content
    assert "[2026-10-08 10:26:24]" in content
    assert "Rate Limit exceeded for 404" in content
    assert "BPJS Add Antrean rejected" in content
    assert result.metadata["ocr_lines"] >= 8

    # 4. OCR-004: Verifikasi pembersihan artefak tepi
    assert not content.startswith('")')
    assert "2oO0" not in content


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract belum terpasang di sistem")
def test_synthetic_terminal_log_with_ground_truth(tmp_path: Path, parser):
    """Fixture sintetis terminal gelap dengan ground truth untuk mengukur CER/WER."""
    img_path = tmp_path / "synthetic_terminal.png"
    ground_truth_lines = [
        "[2026-10-22 09:00:00] INFO: Server initialized on port 8031",
        "[2026-10-22 09:00:01] WARNING: Rate limit approaching for client",
        "[2026-10-22 09:00:02] ERROR: Database connection timeout in pool",
    ]
    gt_text = "\n".join(ground_truth_lines)

    # Buat screenshot terminal background gelap dengan font realistis
    font = _get_font(20)
    img = Image.new("RGB", (900, 200), color=(15, 20, 35))
    draw = ImageDraw.Draw(img)
    y_pos = 25
    for line in ground_truth_lines:
        draw.text((30, y_pos), line, font=font, fill=(220, 225, 240))
        y_pos += 45
    img.save(img_path)

    result = parser.parse(img_path)
    assert result.metadata["has_ocr_text"] is True
    assert result.metadata["is_dark_background"] is True
    assert result.metadata["image_type"] == "LOG_OR_CODE"

    extracted_lines = [
        l.strip() for l in result.content.split("```log\n")[1].split("\n```")[0].splitlines()
        if l.strip()
    ]
    extracted_text = "\n".join(extracted_lines)

    cer = calculate_cer(gt_text, extracted_text)
    # CER harus sangat rendah (< 10%) pada gambar teks sintetis bersih
    assert cer < 0.10, f"CER terlalu tinggi: {cer:.3f}"
    assert "8031" in extracted_text


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract belum terpasang di sistem")
def test_synthetic_simple_logo_short_text(tmp_path: Path, parser):
    """Fixture logo sederhana dengan teks pendek."""
    img_path = tmp_path / "simple_logo.png"
    font = _get_font(24)
    img = Image.new("RGB", (400, 150), color=(245, 245, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 80, 80], fill=(40, 100, 220))
    draw.text((100, 50), "FILE2MD LOGO", font=font, fill=(20, 20, 20))
    img.save(img_path)

    result = parser.parse(img_path)
    assert result.metadata["has_ocr_text"] is True
    assert "FILE2MD" in result.content.upper()


def test_synthetic_photo_no_text(tmp_path: Path, parser):
    """Fixture foto/ilustrasi gradien natural tanpa teks."""
    img_path = tmp_path / "gradient_photo.png"
    # Buat gradien multiwarna halus (foto natural)
    img = Image.new("RGB", (300, 300))
    for x in range(300):
        for y in range(300):
            img.putpixel((x, y), (int(x * 255 / 300), int(y * 255 / 300), 180))
    img.save(img_path)

    result = parser.parse(img_path)
    assert result.metadata["image_type"] == "PHOTO_OR_ILLUSTRATION"
    assert result.metadata["content_label"] == "Photo / Graphic Illustration"
    assert result.metadata["has_ocr_text"] is False


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract belum terpasang di sistem")
def test_wide_aspect_ratio_banner(tmp_path: Path, parser):
    """Fixture gambar sangat lebar / banner rasio > 5:1."""
    img_path = tmp_path / "wide_banner.png"
    font = _get_font(22)
    img = Image.new("RGB", (1200, 150), color=(20, 25, 40))
    draw = ImageDraw.Draw(img)
    draw.text((40, 55), "WIDE BANNER SYSTEM NOTIFICATION OK", font=font, fill=(250, 250, 250))
    img.save(img_path)

    result = parser.parse(img_path)
    assert result.metadata["aspect_ratio"] == "8:1"
    assert result.metadata["has_ocr_text"] is True
    assert "WIDE BANNER" in result.content.upper()


def test_conflict_resolution_vision_vs_log():
    """Memverifikasi resolusi konflik: halusinasi visual diabaikan pada tipe LOG_OR_CODE."""
    dummy_img = Image.new("RGB", (1600, 165), color=(10, 15, 30))
    ocr_text = "[2026-10-08 10:26:24] production.WARNING: Rate Limit exceeded"

    classification = OCRService.classify_image(dummy_img, ocr_text)
    assert classification["image_type"] == "LOG_OR_CODE"
    assert classification["can_use_vision"] is False


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract belum terpasang di sistem")
def test_low_resolution_small_text_upscaling(tmp_path: Path, parser):
    """Fixture teks kecil / resolusi rendah untuk menguji upscaling adaptif."""
    img_path = tmp_path / "small_text.png"
    font = _get_font(14)
    # Gambar kecil 300 x 80 px
    img = Image.new("RGB", (300, 80), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((15, 25), "STATUS CODE: 200 OK", font=font, fill=(0, 0, 0))
    img.save(img_path)

    result = parser.parse(img_path)
    assert result.metadata["has_ocr_text"] is True
    assert "200" in result.content

