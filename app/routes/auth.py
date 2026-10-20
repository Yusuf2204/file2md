import hashlib
import re
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Schemas ---
# --- Schemas ---
class RegisterRequest(BaseModel):
    email: str = Field(..., description="Alamat email pengguna")
    password: str = Field(min_length=6, description="Password minimal 6 karakter")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[\w\.\+-]+@[\w\.-]+\.\w+$", v):
            raise ValueError("Format email tidak valid.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    email: str
    tier: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TierQuotaResponse(BaseModel):
    user: UserResponse
    max_file_size_mb: int
    max_bundle_files: int


class ToggleTierRequest(BaseModel):
    target_tier: str | None = None


# --- Dependency untuk Mendapatkan User dari Token atau API Key ---
def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """
    Mendukung autentikasi via:
    1. Header 'X-API-Key: f2md_live_...' (Personal API Key)
    2. Header 'Authorization: Bearer <token>' (JWT)
    3. Cookie 'access_token' (JWT Session Browser)
    """
    # 1. Cek dari Header X-API-Key
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header and api_key_header.startswith("f2md_"):
        key_hash = hashlib.sha256(api_key_header.strip().encode()).hexdigest()
        key_record = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
            .first()
        )
        if key_record and key_record.user and key_record.user.is_active:
            # Perbarui waktu terakhir digunakan
            key_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return key_record.user

    # 2. Cek dari Authorization Header (Bearer JWT)
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # 3. Cek dari Cookie jika header kosong
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    user_id = int(payload["sub"])
    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def get_current_user(
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Dependency ketat: wajib login (melempar 401 jika guest)."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan. Silakan login terlebih dahulu.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


# --- Endpoints ---
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    # Cek apakah email sudah terdaftar
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar. Silakan gunakan email lain atau login.",
        )

    # Simpan user baru dengan hash password
    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        tier="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Buat JWT
    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})

    # Set cookie untuk browser Web UI
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")

    return AuthResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, tier=user.tier, created_at=user.created_at),
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "tier": user.tier})
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")

    return AuthResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, tier=user.tier, created_at=user.created_at),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Berhasil logout."}


@router.get("/me", response_model=TierQuotaResponse)
def get_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    # Kuota sesuai tier
    if current_user.tier == "pro":
        max_size, max_bundle = 100, 50
    else:  # 'free'
        max_size, max_bundle = 50, 15

    return TierQuotaResponse(
        user=UserResponse(
            id=current_user.id,
            email=current_user.email,
            tier=current_user.tier,
            created_at=current_user.created_at,
        ),
        max_file_size_mb=max_size,
        max_bundle_files=max_bundle,
    )


@router.post("/toggle-tier", summary="Ubah atau toggle tier akun (Free <-> PRO) untuk simulasi/testing")
def toggle_tier(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    req: ToggleTierRequest | None = None,
):
    target = req.target_tier.lower() if req and req.target_tier else None
    if target in ("free", "pro"):
        current_user.tier = target
    else:
        current_user.tier = "pro" if current_user.tier == "free" else "free"

    db.commit()
    db.refresh(current_user)

    # Buat JWT baru dengan tier terbaru & perbarui cookie
    new_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email, "tier": current_user.tier}
    )
    response.set_cookie(key="access_token", value=new_token, httponly=True, samesite="lax")

    return {
        "message": f"Status tier berhasil diubah ke {current_user.tier.upper()}!",
        "tier": current_user.tier,
        "access_token": new_token,
    }
