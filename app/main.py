import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.models import User, ConversionHistory  # Daftarkan model tabel
from app.routes.auth import router as auth_router
from app.routes.conversion import router as conversion_router
from app.routes.history import router as history_router
from app.routes.pages import router as pages_router
from app.services.janitor import start_janitor_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inisialisasi tabel database SQLite jika belum ada
    Base.metadata.create_all(bind=engine)

    # STARTUP: Jalankan background task janitor
    janitor_task = asyncio.create_task(
        start_janitor_loop(temp_dir="temp", interval_seconds=600, max_age_seconds=1800)
    )
    yield
    # SHUTDOWN: Batalkan task janitor secara bersih
    janitor_task.cancel()
    try:
        await janitor_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="File2MD",
    description="Universal File-to-Markdown Converter",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files untuk CSS dan aset
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Daftarkan router
app.include_router(conversion_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(pages_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}