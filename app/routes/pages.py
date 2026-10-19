from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.parsers.base import ParserError
from app.services.converter import ConversionService
from app.services.detector import UnsupportedFormatError

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
service = ConversionService()


@router.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.post("/convert-ui", response_class=HTMLResponse)
def convert_ui(
    request: Request,
    files: list[UploadFile] = File(...),
    bundle_title: str = Form("Project Context"),
):
    if not files:
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={"success": False, "filename": "-", "error": "Tidak ada file yang dipilih."},
        )

    # 1. Mode Single File jika hanya 1 file yang diunggah
    if len(files) == 1:
        f = files[0]
        filename = f.filename or "unknown"
        try:
            output = service.convert_stream(
                file_obj=f.file,
                filename=filename,
                mime_type=f.content_type,
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
    try:
        file_payloads = [(f.file, f.filename or "unknown", f.content_type) for f in files]
        bundle_out = service.bundle_streams(file_payloads, title=bundle_title)

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