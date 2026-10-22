from typing import Annotated, Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.history import ConversionHistory
from app.models.user import User
from app.parsers.base import ParserError
from app.routes.auth import get_current_user_optional
from app.services.converter import ConversionService
from app.services.detector import UnsupportedFormatError
from app.services.security import sanitize_filename

router = APIRouter(prefix="/api", tags=["Conversion"])
service = ConversionService()


def get_tier_limits(user: User | None) -> tuple[int, int]:
    """
    Mengembalikan (max_file_size_bytes, max_bundle_files) berdasarkan status login user.
    - Guest (tanpa login): 10 MB per file, maksimal 3 file bundle.
    - Free User (login): 50 MB per file, maksimal 15 file bundle.
    - Pro User: 100 MB per file, maksimal 50 file bundle.
    """
    if user and user.tier == "pro":
        return (100 * 1024 * 1024, 50)
    elif user:
        return (50 * 1024 * 1024, 15)
    return (10 * 1024 * 1024, 3)


class ConvertResponse(BaseModel):
    filename: str
    markdown: str
    metadata: dict[str, Any]
    warnings: list[str]


@router.post(
    "/convert",
    response_model=ConvertResponse,
    summary="Konversi satu file menjadi Markdown",
    status_code=status.HTTP_200_OK,
)
def convert_file(
    file: UploadFile = File(...),
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    filename = sanitize_filename(file.filename or "unknown")
    max_size, _ = get_tier_limits(current_user)

    try:
        output = service.convert_stream(
            file_obj=file.file,
            filename=filename,
            mime_type=file.content_type,
            max_file_size_bytes=max_size,
        )

        # Simpan ke riwayat jika user sudah login (Tier 2 Value)
        if current_user and db:
            history_record = ConversionHistory(
                user_id=current_user.id,
                filename=output.filename,
                content=output.markdown,
                file_type="single",
            )
            db.add(history_record)
            db.commit()

        return ConvertResponse(
            filename=output.filename,
            markdown=output.markdown,
            metadata=output.metadata,
            warnings=output.warnings,
        )
    except UnsupportedFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses file: {str(exc)}",
        ) from exc


class BundleResponse(BaseModel):
    markdown: str
    total_files: int
    success_files: int
    failed_files: int
    warnings: list[str]


@router.post(
    "/bundle",
    response_model=BundleResponse,
    summary="Gabungkan beberapa file menjadi satu dokumen Markdown (Bundle)",
    status_code=status.HTTP_200_OK,
)
def bundle_files(
    files: list[UploadFile] = File(...),
    title: str = Form("Project Context"),
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada file yang diunggah.",
        )

    max_size, max_files = get_tier_limits(current_user)

    if len(files) > max_files:
        tier_name = current_user.tier.title() if current_user else "Guest"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batas upload bundle untuk akun {tier_name} adalah maksimal {max_files} file "
                f"(Anda mengunggah {len(files)} file). "
                f"Silakan login gratis untuk kuota hingga 15 file!"
            ),
        )

    file_payloads = [
        (f.file, sanitize_filename(f.filename or "unknown"), f.content_type)
        for f in files
    ]

    output = service.bundle_streams(
        file_payloads,
        title=title,
        max_file_size_bytes=max_size,
    )

    # Simpan bundle ke riwayat jika user sudah login
    if current_user and db and output.success_files > 0:
        history_record = ConversionHistory(
            user_id=current_user.id,
            filename=f"{title.replace(' ', '_')}_bundle.md",
            content=output.markdown,
            file_type="bundle",
        )
        db.add(history_record)
        db.commit()

    return BundleResponse(
        markdown=output.markdown,
        total_files=output.total_files,
        success_files=output.success_files,
        failed_files=output.failed_files,
        warnings=output.warnings,
    )