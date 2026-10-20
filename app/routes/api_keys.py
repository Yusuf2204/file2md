import hashlib
import secrets
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(default="CLI Key", max_length=100, description="Label/nama pengenal API key")


class KeyItemResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None

    @field_serializer("created_at", "last_used_at")
    def serialize_dt(self, dt: datetime | None, _info) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class CreateKeyResponse(BaseModel):
    id: int
    name: str
    api_key: str
    key_prefix: str
    created_at: datetime
    message: str

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


@router.get("", response_model=list[KeyItemResponse], summary="Daftar API Key aktif milik user")
def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_user.tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses API Keys hanya tersedia untuk akun PRO.",
        )

    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id, ApiKey.is_active.is_(True))
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return keys


@router.post("", response_model=CreateKeyResponse, status_code=status.HTTP_201_CREATED, summary="Generate API Key baru")
def create_api_key(
    req: CreateKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_user.tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fitur Personal API Key eksklusif untuk tier PRO ke atas. Silakan upgrade akun Anda untuk menggunakan otomasi API & CLI!",
        )

    # Batasi maksimal 10 API key aktif per akun
    active_count = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id, ApiKey.is_active.is_(True))
        .count()
    )
    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batas maksimal 10 API Key aktif telah tercapai. Hapus key lama untuk membuat baru.",
        )

    # 1. Generate token acak berkekuatan tinggi
    raw_token = secrets.token_urlsafe(32)
    api_key_plaintext = f"f2md_live_{raw_token}"

    # 2. Hash key untuk disimpan di database (keamanan zero-plaintext retention)
    key_hash = hashlib.sha256(api_key_plaintext.encode()).hexdigest()
    masked_prefix = f"{api_key_plaintext[:14]}...{api_key_plaintext[-4:]}"

    name = req.name.strip() or "Default Key"

    new_key = ApiKey(
        user_id=current_user.id,
        name=name,
        key_hash=key_hash,
        key_prefix=masked_prefix,
        is_active=True,
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    return CreateKeyResponse(
        id=new_key.id,
        name=new_key.name,
        api_key=api_key_plaintext,
        key_prefix=masked_prefix,
        created_at=new_key.created_at,
        message="Simpan API key Anda sekarang! Demi keamanan, key lengkap ini tidak akan pernah ditampilkan lagi.",
    )


@router.delete("/{key_id}", status_code=status.HTTP_200_OK, summary="Cabut (revoke) API Key")
def delete_api_key(
    key_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    key_obj = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        .first()
    )
    if not key_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key tidak ditemukan.")

    db.delete(key_obj)
    db.commit()
    return {"message": "API Key berhasil dicabut dan dinonaktifkan."}