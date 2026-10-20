import io
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import ApiKey, User
from app.services.security import create_access_token, hash_password
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    db = SessionLocal()
    db.query(ApiKey).delete()
    db.query(User).filter(User.email.like("%@test-apikey.local")).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(ApiKey).delete()
    db.query(User).filter(User.email.like("%@test-apikey.local")).delete()
    db.commit()
    db.close()


def test_free_user_cannot_create_or_list_api_keys():
    """Memastikan user dengan tier Free dilarang membuat atau melihat API keys (HTTP 403 Forbidden)."""
    client.cookies.clear()

    db = SessionLocal()
    free_user = User(
        email="free_user@test-apikey.local",
        hashed_password=hash_password("password123"),
        tier="free",
    )
    db.add(free_user)
    db.commit()
    token = create_access_token(data={"sub": str(free_user.id), "email": free_user.email, "tier": free_user.tier})
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # Free user mencoba membuat API key
    res_create = client.post("/api/keys", json={"name": "CLI Script"}, headers=headers)
    assert res_create.status_code == 403
    assert "eksklusif untuk tier PRO" in res_create.json()["detail"]

    # Free user mencoba melihat daftar API key
    res_list = client.get("/api/keys", headers=headers)
    assert res_list.status_code == 403
    assert "hanya tersedia untuk akun PRO" in res_list.json()["detail"]


def test_toggle_tier_simulation():
    """Menguji endpoint /api/auth/toggle-tier untuk beralih tier Free <-> PRO dengan mulus."""
    client.cookies.clear()

    db = SessionLocal()
    user = User(
        email="toggle_user@test-apikey.local",
        hashed_password=hash_password("password123"),
        tier="free",
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upgrade ke PRO via target_tier
    res_up = client.post("/api/auth/toggle-tier", json={"target_tier": "pro"}, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["tier"] == "pro"
    pro_token = res_up.json()["access_token"]

    # 2. Toggle otomatis tanpa body (harus berubah dari pro kembali ke free)
    pro_headers = {"Authorization": f"Bearer {pro_token}"}
    res_toggle_down = client.post("/api/auth/toggle-tier", json={}, headers=pro_headers)
    assert res_toggle_down.status_code == 200
    assert res_toggle_down.json()["tier"] == "free"

    # 3. Toggle otomatis lagi (harus berubah dari free ke pro)
    free_headers = {"Authorization": f"Bearer {res_toggle_down.json()['access_token']}"}
    res_toggle_up = client.post("/api/auth/toggle-tier", json={}, headers=free_headers)
    assert res_toggle_up.status_code == 200
    assert res_toggle_up.json()["tier"] == "pro"


def test_pro_api_key_lifecycle_and_authentication():
    """Menguji siklus hidup API key untuk user PRO dan otentikasi konversi via X-API-Key."""
    client.cookies.clear()

    # 1. Buat user PRO
    db = SessionLocal()
    pro_user = User(
        email="pro_user@test-apikey.local",
        hashed_password=hash_password("secret123"),
        tier="pro",
    )
    db.add(pro_user)
    db.commit()
    token = create_access_token(data={"sub": str(pro_user.id), "email": pro_user.email, "tier": pro_user.tier})
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Buat API key baru via POST /api/keys
    res_create = client.post("/api/keys", json={"name": "CLI Automation"}, headers=headers)
    assert res_create.status_code == 201
    data = res_create.json()
    assert "api_key" in data
    assert data["api_key"].startswith("f2md_live_")
    assert data["name"] == "CLI Automation"
    raw_key = data["api_key"]
    key_id = data["id"]

    # 3. Dapatkan daftar API key via GET /api/keys
    res_list = client.get("/api/keys", headers=headers)
    assert res_list.status_code == 200
    keys = res_list.json()
    assert len(keys) == 1
    assert "api_key" not in keys[0]  # Plaintext key tidak dibocorkan di list
    assert keys[0]["key_prefix"].startswith("f2md_live_")

    # 4. Uji autentikasi endpoint /api/convert menggunakan header X-API-Key (tanpa token JWT/Cookie)
    client.cookies.clear()
    api_headers = {"X-API-Key": raw_key}
    file_content = b"# Laporan Otomasi\nKonversi via cURL berhasil 100%."
    files = {"file": ("laporan.txt", io.BytesIO(file_content), "text/plain")}

    res_conv = client.post("/api/convert", files=files, headers=api_headers)
    assert res_conv.status_code == 200
    assert "Laporan Otomasi" in res_conv.json()["markdown"]

    # 5. Cabut (Revoke) key via DELETE /api/keys/{key_id}
    res_del = client.delete(f"/api/keys/{key_id}", headers=headers)
    assert res_del.status_code == 200

    # 6. Pastikan daftar key sekarang kosong
    res_del_list = client.get("/api/keys", headers=headers)
    assert len(res_del_list.json()) == 0

    assert len(res_del_list.json()) == 0