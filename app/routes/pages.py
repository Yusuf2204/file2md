from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.routes.auth import get_current_user_optional
from app.routes.conversion import get_tier_limits
from app.services.converter import ConversionService

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
service = ConversionService()


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": current_user},
    )


@router.post("/convert-ui", response_class=HTMLResponse)
def convert_ui(
    request: Request,
    files: list[UploadFile] = File(...),
    bundle_title: str = Form("Project Context"),
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
):
    if not files:
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={"success": False, "filename": "-", "error": "Tidak ada file yang dipilih."},
        )

    max_size, max_files = get_tier_limits(current_user)

    # 1. Mode Single File jika hanya 1 file yang diunggah
    if len(files) == 1:
        f = files[0]
        filename = f.filename or "unknown"
        try:
            output = service.convert_stream(
                file_obj=f.file,
                filename=filename,
                mime_type=f.content_type,
                max_file_size_bytes=max_size,
            )
            return templates.TemplateResponse(
                request=request,
                name="result_partial.html",
                context={
                    "success": True,
                    "filename": output.filename,
                    "markdown": output.markdown,
                    "metadata": output.metadata,
                    "warnings": output.warnings,
                },
            )
        except Exception as exc:
            return templates.TemplateResponse(
                request=request,
                name="result_partial.html",
                context={"success": False, "filename": filename, "error": str(exc)},
            )

    # 2. Mode Bundle jika lebih dari 1 file
    if len(files) > max_files:
        tier_label = current_user.tier.title() if current_user else "Tamu (Guest)"
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={
                "success": False,
                "filename": "Bundle Limit",
                "error": (
                    f"Batas upload bundle untuk akun {tier_label} adalah maksimal {max_files} file "
                    f"(Anda memilih {len(files)} file). "
                    f"Silakan login gratis untuk bundle hingga 15 file!"
                ),
            },
        )

    try:
        file_payloads = [(f.file, f.filename or "unknown", f.content_type) for f in files]
        bundle_out = service.bundle_streams(
            file_payloads,
            title=bundle_title,
            max_file_size_bytes=max_size,
        )

        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={
                "success": True,
                "filename": f"bundle_{len(files)}_files.md",
                "markdown": bundle_out.markdown,
                "metadata": {
                    "mode": "Bundle",
                    "total_files": bundle_out.total_files,
                    "success": bundle_out.success_files,
                    "failed": bundle_out.failed_files,
                },
                "warnings": bundle_out.warnings,
            },
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={
                "success": False,
                "filename": "Bundle",
                "error": f"Gagal membuat bundle: {str(exc)}",
            },
        )