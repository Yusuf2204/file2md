import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_api_convert_txt_success():
    file_bytes = b"Catatan penting\nBaris kedua."
    response = client.post(
        "/api/convert",
        files={"file": ("catatan.txt", io.BytesIO(file_bytes), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "catatan.txt"
    assert data["markdown"] == "Catatan penting\nBaris kedua."
    assert data["metadata"]["line_count"] == 2


def test_api_convert_json_success():
    file_bytes = b'{"status": "ok", "items": [1, 2]}'
    response = client.post(
        "/api/convert",
        files={"file": ("data.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "data.json"
    assert "```json" in data["markdown"]


def test_api_convert_unsupported_format():
    file_bytes = b"binary exe content"
    response = client.post(
        "/api/convert",
        files={"file": ("malware.exe", io.BytesIO(file_bytes), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "belum didukung" in response.json()["detail"]


def test_api_convert_invalid_json():
    file_bytes = b'{"bad_json": '
    response = client.post(
        "/api/convert",
        files={"file": ("bad.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert response.status_code == 422
    assert "Format JSON tidak valid" in response.json()["detail"]