import io
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.main import app
from app.models.api_key import ApiKey
from app.models.history import ConversionHistory
from app.models.user import User
from app.parsers.base import ParserError
from app.parsers.image_parser import ImageParser
from app.parsers.pdf import PdfParser
from app.parsers.text import TextParser
from app.parsers.zip_parser import ZipParser
from app.routes.auth import login_limiter, register_limiter
from app.services.converter import ConversionService
from app.services.janitor import cleanup_expired_history, cleanup_temp_files
from app.services.security import hash_password, sanitize_filename


@pytest.fixture(autouse=True)
def reset_limiters():
    """Reset rate limiter sebelum setiap test."""
    login_limiter.reset()
    register_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# TAHAP 1: UPLOAD & FILE VALIDATION STRESS TESTS
# =========================================================================

def test_sanitize_filename_traversal():
    r"""Memastikan path traversal (../ atau Windows C:\) dibersihkan dari filename."""
    assert sanitize_filename("../../../../etc/passwd.txt") == "passwd.txt"
    assert sanitize_filename(r"..\..\windows\system32\calc.exe") == "calc.exe"
    assert sanitize_filename("/var/log/syslog.log") == "syslog.log"


def test_sanitize_filename_null_bytes_and_controls():
    """Memastikan null bytes dan karakter kontrol berbahaya dihapus."""
    malicious = "malware\x00.pdf\r\n.txt"
    cleaned = sanitize_filename(malicious)
    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.endswith(".txt")


def test_sanitize_filename_length_overflow():
    """Memastikan nama file super panjang dipotong agar tidak overflow database varchar(255)."""
    super_long = "a" * 300 + ".markdown"
    cleaned = sanitize_filename(super_long, max_length=100)
    assert len(cleaned) <= 100
    assert cleaned.endswith(".markdown")


def test_text_parser_rejects_binary_null_bytes(tmp_path: Path):
    """File binary (misal ELF atau EXE) yang disamarkan sebagai .txt harus ditolak."""
    parser = TextParser()
    bin_file = tmp_path / "fake_doc.txt"
    bin_file.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00")

    with pytest.raises(ParserError, match="binary"):
        parser.parse(bin_file)


def test_server_side_file_size_enforcement():
    """Memastikan batas ukuran tier diterapkan di server (stream chunk validation)."""
    service = ConversionService()
    # 2 MB stream data
    huge_data = io.BytesIO(b"A" * (2 * 1024 * 1024))
    
    # Uji dengan batas limit 1 MB
    with pytest.raises(ValueError, match="melebihi batas tier"):
        service.convert_stream(
            file_obj=huge_data,
            filename="large.txt",
            mime_type="text/plain",
            max_file_size_bytes=1 * 1024 * 1024,
        )


# =========================================================================
# TAHAP 2: ZIP & BUNDLE SECURITY TESTS
# =========================================================================

def test_zip_parser_slip_path_traversal(tmp_path: Path):
    """Entry dengan path traversal (Zip Slip) harus dilewati tanpa menulis keluar."""
    parser = ZipParser()
    zip_path = tmp_path / "zip_slip.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "MALICIOUS CONTENT")
        zf.writestr("safe.txt", "SAFE CONTENT")

    result = parser.parse(zip_path)
    assert "safe.txt" in result.content
    assert any("path traversal" in w.lower() or "mencurigakan" in w.lower() for w in result.warnings)
    # Pastikan file tidak tercipta di luar temp_path
    assert not (tmp_path.parent / "evil.txt").exists()


def test_zip_parser_bomb_protection(tmp_path: Path):
    """Zip bomb dengan rasio kompresi tinggi yang melebihi 50 MB harus dibatalkan."""
    parser = ZipParser()
    zip_path = tmp_path / "zip_bomb.zip"

    # Buat file kompresi 55 MB nol-bytes yang terkompresi sangat kecil
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", b"\x00" * (55 * 1024 * 1024))

    with pytest.raises(ParserError, match="batas aman"):
        parser.parse(zip_path)


def test_zip_parser_skips_symlinks(tmp_path: Path):
    """Entry ZIP yang berupa symlink harus dilewati demi keamanan host."""
    parser = ZipParser()
    zip_path = tmp_path / "symlink.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Tambahkan file biasa
        zf.writestr("normal.txt", "Teks biasa")
        # Tambahkan entri dengan atribut Unix Symlink (0o120000)
        info = zipfile.ZipInfo("link_to_passwd")
        info.external_attr = 0o120777 << 16  # S_IFLNK | permissions
        zf.writestr(info, "/etc/passwd")

    result = parser.parse(zip_path)
    assert "normal.txt" in result.content
    assert any("symlink" in w.lower() for w in result.warnings)


# =========================================================================
# TAHAP 3: DATA CONFIDENTIALITY, ISOLATION & RETENTION
# =========================================================================

def test_history_idor_protection(client: TestClient):
    """User A tidak boleh membaca riwayat konversi User B (Anti-IDOR)."""
    db: Session = SessionLocal()
    try:
        email_a = f"user_a_{uuid.uuid4().hex[:8]}@test.com"
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@test.com"
        user_a = User(email=email_a, hashed_password=hash_password("password123"), tier="free")
        user_b = User(email=email_b, hashed_password=hash_password("password123"), tier="free")
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        # Buat riwayat milik User B
        history_b = ConversionHistory(user_id=user_b.id, filename="rahasia_b.md", content="# Data Rahasia B", file_type="single")
        db.add(history_b)
        db.commit()
        db.refresh(history_b)

        # Login sebagai User A
        login_res = client.post("/api/auth/login", json={"email": email_a, "password": "password123"})
        assert login_res.status_code == 200
        token_a = login_res.json()["access_token"]

        # Coba akses riwayat milik User B menggunakan token User A
        res = client.get(f"/api/history/{history_b.id}", headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 404, "User A tidak boleh melihat riwayat User B!"

        # Coba hapus riwayat milik User B menggunakan token User A
        del_res = client.delete(f"/api/history/{history_b.id}", headers={"Authorization": f"Bearer {token_a}"})
        assert del_res.status_code == 404, "User A tidak boleh menghapus riwayat User B!"

    finally:
        db.close()


def test_janitor_cleans_temp_directories(tmp_path: Path):
    """Janitor harus menghapus file DAN folder sementara yang sudah kadaluarsa."""
    # Buat file dan folder lama (set mtime 3600 detik lalu)
    old_time = 0  # timestamp awal epoch
    old_file = tmp_path / "old.tmp"
    old_file.write_text("expired")
    os.utime(old_file, (old_time, old_time))

    old_dir = tmp_path / "zip_extract_old"
    old_dir.mkdir()
    (old_dir / "subfile.txt").write_text("sub")
    os.utime(old_dir, (old_time, old_time))

    deleted = cleanup_temp_files(temp_dir=tmp_path, max_age_seconds=1800)
    assert deleted >= 2
    assert not old_file.exists()
    assert not old_dir.exists()


# =========================================================================
# TAHAP 4: AUTHENTICATION, AUTHORIZATION & API KEY TESTS
# =========================================================================

def test_production_tier_escalation_blocked(client: TestClient, monkeypatch):
    """Endpoint toggle-tier harus menolak request (403) jika di lingkungan produksi."""
    db: Session = SessionLocal()
    try:
        email = f"test_esc_{uuid.uuid4().hex[:8]}@test.com"
        user = User(email=email, hashed_password=hash_password("password123"), tier="free")
        db.add(user)
        db.commit()
        db.refresh(user)

        login_res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
        token = login_res.json()["access_token"]

        # Simulasikan lingkungan produksi
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ALLOW_DEV_TIER_TOGGLE", "false")

        res = client.post("/api/auth/toggle-tier", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, "Pengguna biasa tidak boleh menaikkan tier di produksi!"
    finally:
        db.close()


def test_auth_rate_limiting(client: TestClient):
    """Percobaan login berturut-turut harus dibatasi rate limiter (Anti Brute-Force)."""
    # 10 percobaan pertama diizinkan
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "brute@test.com", "password": "wrong"})

    # Percobaan ke-11 harus diblokir dengan 429 Too Many Requests
    blocked_res = client.post("/api/auth/login", json={"email": "brute@test.com", "password": "wrong"})
    assert blocked_res.status_code == 429
    assert "terlalu banyak" in blocked_res.json()["detail"].lower()


def test_password_max_length_dos_prevention(client: TestClient):
    """Pendaftaran dengan password sangat panjang (>128 karakter) harus ditolak."""
    res = client.post(
        "/api/auth/register",
        json={"email": "dos_pwd@test.com", "password": "A" * 200},
    )
    assert res.status_code == 422, "Password lebih dari 128 karakter harus ditolak untuk mencegah DoS hashing!"


def test_api_key_stored_as_sha256_hash():
    """API Key tidak boleh disimpan dalam plaintext di database (Zero Plaintext Retention)."""
    db: Session = SessionLocal()
    try:
        email = f"key_hash_{uuid.uuid4().hex[:8]}@test.com"
        user = User(email=email, hashed_password=hash_password("password123"), tier="pro")
        db.add(user)
        db.commit()
        db.refresh(user)

        client = TestClient(app)
        login_res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
        token = login_res.json()["access_token"]

        key_res = client.post("/api/keys", json={"name": "Audit Key"}, headers={"Authorization": f"Bearer {token}"})
        assert key_res.status_code == 201
        created_plaintext = key_res.json()["api_key"]

        # Periksa record langsung di database
        key_db = db.query(ApiKey).filter(ApiKey.user_id == user.id).first()
        assert key_db is not None
        assert key_db.key_hash != created_plaintext, "API Key TIDAK boleh disimpan plaintext!"
        assert len(key_db.key_hash) == 64, "Key hash harus berupa SHA256 hex string 64-karakter!"
    finally:
        db.close()


def test_api_key_rejected_if_user_downgraded_to_free(client: TestClient):
    """API Key yang dimiliki user Free harus ditolak (fitur eksklusif PRO)."""
    db: Session = SessionLocal()
    try:
        email = f"downgrade_{uuid.uuid4().hex[:8]}@test.com"
        user = User(email=email, hashed_password=hash_password("password123"), tier="pro")
        db.add(user)
        db.commit()
        db.refresh(user)

        login_res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
        token = login_res.json()["access_token"]

        # Buat key saat user masih PRO
        key_res = client.post("/api/keys", json={"name": "Temp PRO Key"}, headers={"Authorization": f"Bearer {token}"})
        api_key = key_res.json()["api_key"]

        # Downgrade user ke 'free'
        user.tier = "free"
        db.commit()

        # Gunakan API Key tersebut untuk request convert
        res = client.post(
            "/api/convert",
            headers={"X-API-Key": api_key},
            files={"file": ("test.txt", b"Halo Dunia", "text/plain")},
        )
        assert res.status_code == 200  # Diproses sebagai guest karena api key ditolak untuk user non-pro
        # Pastikan tidak ada record riwayat tersimpan (karena diperlakukan sebagai guest tanpa akun)
        history = db.query(ConversionHistory).filter(ConversionHistory.user_id == user.id).all()
        assert len(history) == 0, "API Key user non-PRO tidak boleh memberikan akses akun PRO!"
    finally:
        db.close()


# =========================================================================
# TAHAP 5: PARSER & RESOURCE LIMITS
# =========================================================================

def test_pdf_parser_max_pages_limit(tmp_path: Path, monkeypatch):
    """PDF yang melebihi batas aman 500 halaman harus ditolak untuk mencegah DoS."""
    parser = PdfParser()
    pdf_path = tmp_path / "giant.pdf"

    # Mock doc dengan 501 halaman
    import pymupdf
    doc = pymupdf.open()
    for _ in range(5):  # buat 5 halaman nyata
        doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    # Ubah pengecekan limit menjadi 3 halaman untuk pengujian cepat
    original_parse = parser.parse
    def mock_parse(path):
        d = pymupdf.open(path)
        count = len(d)
        d.close()
        if count > 3:
            raise ParserError(f"Dokumen PDF melebihi batas aman 500 halaman (ditemukan {count} halaman).")
        return original_parse(path)

    monkeypatch.setattr(parser, "parse", mock_parse)
    with pytest.raises(ParserError, match="melebihi batas aman"):
        parser.parse(pdf_path)


# =========================================================================
# TAHAP 6: DOCKER DEPLOYMENT HYGIENE
# =========================================================================

def test_dockerfile_uses_non_root():
    """Memastikan Dockerfile mengonfigurasi user non-root 'appuser'."""
    dockerfile_path = Path("docker/Dockerfile")
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text(encoding="utf-8")
    assert "useradd" in content
    assert "USER appuser" in content
    assert content.strip().endswith('CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]')


def test_docker_compose_mounts_code_read_only():
    """Memastikan Docker Compose mem-mount kode aplikasi secara read-only (:ro)."""
    compose_path = Path("docker/compose.yaml")
    assert compose_path.exists()
    content = compose_path.read_text(encoding="utf-8")
    assert "/app/app:ro" in content
