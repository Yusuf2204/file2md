from typing import Any
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from app.parsers.base import ParserError
from app.services.converter import ConversionService
from app.services.detector import UnsupportedFormatError

router = APIRouter(prefix="/api", tags=["Conversion"])
service = ConversionService()


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
def convert_file(file: UploadFile = File(...)):
    filename = file.filename or "unknown"

    try:
        output = service.convert_stream(
            file_obj=file.file,
            filename=filename,
            mime_type=file.content_type,
        )
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
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada file yang diunggah.",
        )

    file_payloads = [
        (f.file, f.filename or "unknown", f.content_type)
        for f in files
    ]

    output = service.bundle_streams(file_payloads, title=title)

    return BundleResponse(
        markdown=output.markdown,
        total_files=output.total_files,
        success_files=output.success_files,
        failed_files=output.failed_files,
        warnings=output.warnings,
    )