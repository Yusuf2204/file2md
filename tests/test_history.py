import io
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import ConversionHistory, User
from app.services.janitor import cleanup_expired_history
from app.services.security import create_access_token, hash_password
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    db.query(ConversionHistory).delete()
    db.query(User).filter(User.email.like("%@test-history.local")).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(ConversionHistory).delete()
    db.query(User).filter(User.email.like("%@test-history.local")).delete()
    db.commit()
    db.close()


def test_history_lifecycle():
    client.cookies.clear()

    # 1. Buat user terdaftar
    db = SessionLocal()
    user = User(
        email="history_user@test-history.local",
        hashed_password=hash_password("pass123"),
        tier="free",
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload file dengan token login
    file_content = b"# Catatan Penting\nIsi teks dokumen rahasia."
    files = {"file": ("catatan.txt", io.BytesIO(file_content), "text/plain")}
    res_conv = client.post("/api/convert", files=files, headers=headers)
    assert res_conv.status_code == 200

    # 3. Cek daftar riwayat di GET /api/history
    res_hist = client.get("/api/history", headers=headers)
    assert res_hist.status_code == 200
    items = res_hist.json()
    assert len(items) == 1
    assert items[0]["filename"] == "catatan.txt"
    history_id = items[0]["id"]

    # 4. Ambil isi detail Markdown dari riwayat
    res_detail = client.get(f"/api/history/{history_id}", headers=headers)
    assert res_detail.status_code == 200
    assert "Catatan Penting" in res_detail.json()["content"]

    # 5. Hapus riwayat
    res_del = client.delete(f"/api/history/{history_id}", headers=headers)
    assert res_del.status_code == 200

    # Pastikan sudah kosong
    res_after = client.get("/api/history", headers=headers)
    assert len(res_after.json()) == 0


def test_guest_conversion_does_not_create_history():
    client.cookies.clear()

    # Guest upload file
    file_content = b"Halo dunia tanpa login"
    files = {"file": ("guest_file.txt", io.BytesIO(file_content), "text/plain")}
    res = client.post("/api/convert", files=files)
    assert res.status_code == 200

    # Pastikan database conversion_history tetap kosong
    db = SessionLocal()
    count = db.query(ConversionHistory).count()
    db.close()
    assert count == 0, "Guest upload tidak boleh disimpan di database history!"


def test_janitor_cleans_expired_history():
    db = SessionLocal()
    # Buat user dummy
    user = User(
        email="janitor_user@test-history.local",
        hashed_password=hash_password("pass123"),
        tier="free",
    )
    db.add(user)
    db.commit()

    # Buat 1 riwayat yang sudah kadaluarsa (kemarin)
    past_time = datetime.now(timezone.utc) - timedelta(hours=25)
    expired_item = ConversionHistory(
        user_id=user.id,
        filename="expired.txt",
        content="teks basi",
        expires_at=past_time,
    )
    # Buat 1 riwayat yang masih aktif (besok)
    future_time = datetime.now(timezone.utc) + timedelta(hours=20)
    active_item = ConversionHistory(
        user_id=user.id,
        filename="active.txt",
        content="teks segar",
        expires_at=future_time,
    )
    db.add_all([expired_item, active_item])
    db.commit()

    # Jalankan janitor pembersih riwayat
    cleaned = cleanup_expired_history()
    assert cleaned == 1

    remaining = db.query(ConversionHistory).filter(ConversionHistory.user_id == user.id).all()
    assert len(remaining) == 1
    assert remaining[0].filename == "active.txt"
    db.close()


def test_convert_ui_creates_history_for_logged_in_user():
    client.cookies.clear()
    db = SessionLocal()
    user = User(
        email="ui_user@test-history.local",
        hashed_password=hash_password("pass123"),
        tier="free",
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})
    db.close()

    client.cookies.set("access_token", token)

    # 1. Test GET / renders empty history state with sidebar
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "has-sidebar" in res_index.text
    assert "Belum ada riwayat konversi." in res_index.text
    assert 'id="history-count">0 file' in res_index.text

    # 2. Test POST /convert-ui adds history
    files = [("files", ("ui_test.txt", io.BytesIO(b"# Hello from UI"), "text/plain"))]
    res_ui = client.post("/convert-ui", files=files)
    assert res_ui.status_code == 200
    assert "Hasil Konversi" in res_ui.text

    # 3. Verify GET /api/history returns the new record
    res_hist = client.get("/api/history")
    assert res_hist.status_code == 200
    items = res_hist.json()
    assert len(items) == 1
    assert items[0]["filename"] == "ui_test.txt"
