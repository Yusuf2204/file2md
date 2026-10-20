import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Pastikan folder data/ ada untuk menyimpan file2md.db
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# URL Database: default menggunakan SQLite lokal
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/file2md.db")

# Jika SQLite, butuh check_same_thread=False agar aman dipakai multithread FastAPI
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Pabrik pembuat sesi database (Session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class untuk semua model tabel
Base = declarative_base()


def get_db():
    """
    Dependency FastAPI untuk inject sesi database ke route.
    Sesi otomatis ditutup setelah request selesai (mirip try-finally).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()