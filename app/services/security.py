import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
import jwt

# Secret key untuk menandatangani JWT (dapat diubah via Environment Variable)
SECRET_KEY = os.getenv("SECRET_KEY", "file2md-secret-key-super-secure-change-in-prod-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 hari


def hash_password(password: str) -> str:
    """
    Menghasilkan hash password yang aman menggunakan PBKDF2-HMAC-SHA256 dengan random salt 16-byte.
    Format output: <salt_hex>$<hash_hex>
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Memverifikasi apakah password plain cocok dengan hash yang tersimpan.
    Menggunakan secrets.compare_digest untuk mencegah timing attack.
    """
    try:
        salt, stored_hash = hashed_password.split("$")
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return secrets.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Membuat JSON Web Token (JWT) dengan payload dan masa berlaku kadaluarsa.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Mendekode dan memverifikasi tanda tangan JWT. Mengembalikan payload jika valid, None jika invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Membersihkan nama file dari path traversal, null bytes, dan karakter berbahaya.
    Mencegah directory traversal dan buffer length overflow pada database/filesystem.
    """
    if not filename:
        return "unnamed_file"

    # 1. Hapus null bytes dan karakter kontrol
    clean = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # 2. Normalisasi backslash Windows menjadi slash agar cross-platform
    clean = clean.replace("\\", "/")

    # 3. Ambil hanya nama file dasar (basename)
    clean = Path(clean).name

    # 4. Ganti karakter terlarang filesystem
    clean = re.sub(r'[\\/*?:"<>|]', "_", clean)
    clean = clean.strip(". ")

    if not clean:
        clean = "unnamed_file"

    # 4. Potong panjang jika melebihi batas, tetapi pertahankan ekstensi
    if len(clean) > max_length:
        p = Path(clean)
        ext = p.suffix
        stem = p.stem[: max_length - len(ext)]
        clean = f"{stem}{ext}"

    return clean
