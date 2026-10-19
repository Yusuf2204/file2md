from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes.conversion import router as conversion_router
from app.routes.pages import router as pages_router

app = FastAPI(
    title="File2MD",
    description="Universal File-to-Markdown Converter",
    version="1.0.0",
)

# Static files untuk CSS dan aset
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Daftarkan router
app.include_router(conversion_router)
app.include_router(pages_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}