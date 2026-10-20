import re
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
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


# --- Dependency untuk Mendapatkan User dari Token ---
def get_current_user_optional(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """
    Mendukung token dari Header 'Authorization: Bearer <token>' ATAU Cookie 'access_token'.
    Mengembalikan None jika user adalah Guest (belum login).
    """
    token = None
    # 1. Cek dari Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # 2. Cek dari Cookie jika header kosong
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