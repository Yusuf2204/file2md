import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import User
from app.main import app

# Pastikan tabel SQLite dibuat
Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_user():
    """Otomatis membersihkan user testing sebelum dan sesudah setiap test."""
    # 1. Bersihkan sebelum test
    db = SessionLocal()
    db.query(User).filter(User.email == "tester_auth@file2md.local").delete()
    db.commit()
    db.close()

    yield

    # 2. Bersihkan setelah test selesai
    db = SessionLocal()
    db.query(User).filter(User.email == "tester_auth@file2md.local").delete()
    db.commit()
    db.close()


def test_register_and_login_flow():
    test_email = "tester_auth@file2md.local"
    test_password = "password12345"

    client.cookies.clear()

    # 1. Register user baru (sekarang dijamin selalu dapat 201)
    res_reg = client.post(
        "/api/auth/register",
        json={"email": test_email, "password": test_password},
    )
    assert res_reg.status_code == 201
    data_reg = res_reg.json()
    assert "access_token" in data_reg
    assert data_reg["user"]["email"] == test_email
    assert data_reg["user"]["tier"] == "free"

    token = data_reg["access_token"]

    # 2. Cek endpoint /me dengan Header Authorization
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    data_me = res_me.json()
    assert data_me["user"]["email"] == test_email
    assert data_me["max_file_size_mb"] == 50
    assert data_me["max_bundle_files"] == 15

    # 3. Register ulang dengan email sama harus ditolak (400)
    res_dup = client.post(
        "/api/auth/register",
        json={"email": test_email, "password": test_password},
    )
    assert res_dup.status_code == 400

    # 4. Login dengan password salah harus ditolak (401)
    res_wrong = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": "wrongpassword"},
    )
    assert res_wrong.status_code == 401

    # 5. Login dengan password benar harus berhasil (200)
    res_login = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()


def test_me_unauthorized_without_token():
    client.cookies.clear()
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Autentikasi diperlukan" in res.json()["detail"]