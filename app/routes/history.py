from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_serializer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.history import ConversionHistory
from app.models.user import User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/history", tags=["History"])


class HistoryItemResponse(BaseModel):
    id: int
    filename: str
    file_type: str | None
    created_at: datetime
    expires_at: datetime

    @field_serializer("created_at", "expires_at")
    def serialize_dt(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


class HistoryDetailResponse(BaseModel):
    id: int
    filename: str
    content: str
    file_type: str | None
    created_at: datetime
    expires_at: datetime

    @field_serializer("created_at", "expires_at")
    def serialize_dt(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()


@router.get("", response_model=list[HistoryItemResponse], summary="Daftar riwayat konversi user (24 jam)")
def list_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Mengembalikan daftar file yang pernah dikonversi user dalam 24 jam terakhir."""
    items = (
        db.query(ConversionHistory)
        .filter(ConversionHistory.user_id == current_user.id)
        .order_by(ConversionHistory.created_at.desc())
        .all()
    )
    return items


@router.get("/{history_id}", response_model=HistoryDetailResponse, summary="Ambil detail Markdown dari riwayat")
def get_history_detail(
    history_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Membuka kembali isi Markdown file dari riwayat."""
    item = (
        db.query(ConversionHistory)
        .filter(ConversionHistory.id == history_id, ConversionHistory.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Riwayat konversi tidak ditemukan atau sudah kadaluarsa.",
        )
    return item


@router.delete("/{history_id}", status_code=status.HTTP_200_OK, summary="Hapus satu riwayat konversi")
def delete_history_item(
    history_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    item = (
        db.query(ConversionHistory)
        .filter(ConversionHistory.id == history_id, ConversionHistory.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Riwayat tidak ditemukan.")
    
    db.delete(item)
    db.commit()
    return {"message": "Riwayat berhasil dihapus."}