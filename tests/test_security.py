from datetime import timedelta
from app.services.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification():
    raw_password = "RahasiaUser2026!"
    hashed = hash_password(raw_password)

    # Hash tidak boleh sama dengan password mentah
    assert hashed != raw_password
    assert "$" in hashed

    # Password benar harus lolos
    assert verify_password(raw_password, hashed) is True

    # Password salah harus ditolak
    assert verify_password("SalahPassword", hashed) is False


def test_jwt_token_flow():
    user_data = {"sub": "1", "email": "test@file2md.local", "tier": "free"}
    token = create_access_token(data=user_data)

    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["email"] == "test@file2md.local"
    assert payload["tier"] == "free"


def test_jwt_token_expired():
    user_data = {"sub": "1"}
    # Buat token yang sudah expired 1 detik lalu
    expired_token = create_access_token(data=user_data, expires_delta=timedelta(seconds=-1))

    payload = decode_access_token(expired_token)
    assert payload is None, "Token expired harus mengembalikan None"