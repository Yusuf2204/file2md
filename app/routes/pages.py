from fastapi import APIRouter, File, Request, UploadFile
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
def convert_ui(request: Request, file: UploadFile = File(...)):
    filename = file.filename or "unknown"

    try:
        output = service.convert_stream(
            file_obj=file.file,
            filename=filename,
            mime_type=file.content_type,
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
    except (UnsupportedFormatError, ValueError, ParserError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={"success": False, "filename": filename, "error": str(exc)},
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="result_partial.html",
            context={
                "success": False,
                "filename": filename,
                "error": f"Terjadi kesalahan internal: {str(exc)}",
            },
        )