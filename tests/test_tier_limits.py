import io
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.models import User
from app.services.security import create_access_token, hash_password
from app.main import app

Base.metadata.create_all(bind=engine)
client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    # Bersihkan user testing sebelum dan sesudah test
    db = SessionLocal()
    db.query(User).filter(User.email.like("%@test-tier.local")).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(User).filter(User.email.like("%@test-tier.local")).delete()
    db.commit()
    db.close()


def test_guest_bundle_limit_exceeded():
    # Guest hanya boleh maksimal 3 file. Coba unggah 4 file tanpa token/login
    client.cookies.clear()
    files = [
        ("files", (f"file_{i}.txt", io.BytesIO(b"halo"), "text/plain"))
        for i in range(4)
    ]
    res = client.post("/api/bundle", files=files)
    assert res.status_code == 400
    assert "Guest adalah maksimal 3 file" in res.json()["detail"]


def test_registered_user_bundle_allowed():
    client.cookies.clear()
    # Buat user free di database
    db = SessionLocal()
    user = User(
        email="free_user@test-tier.local",
        hashed_password=hash_password("pass123"),
        tier="free",
    )
    db.add(user)
    db.commit()
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})
    db.close()

    # Free user boleh mengunggah 4 file (karena batas free user adalah 15 file)
    files = [
        ("files", (f"file_{i}.txt", io.BytesIO(b"halo"), "text/plain"))
        for i in range(4)
    ]
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/bundle", files=files, headers=headers)
    assert res.status_code == 200
    assert res.json()["total_files"] == 4