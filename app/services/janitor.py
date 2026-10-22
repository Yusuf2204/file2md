import asyncio
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from app.database import SessionLocal
from app.models.history import ConversionHistory

logger = logging.getLogger("file2md.janitor")


def cleanup_temp_files(temp_dir: Path | str = "temp", max_age_seconds: int = 1800) -> int:
    """
    Memeriksa folder temp dan menghapus file yang berumur lebih dari max_age_seconds.
    Mengembalikan jumlah file yang berhasil dihapus.
    """
    path = Path(temp_dir)
    if not path.exists() or not path.is_dir():
        return 0

    deleted_count = 0
    now = time.time()

    for item in path.iterdir():
        try:
            file_age = now - item.stat().st_mtime
            if file_age > max_age_seconds:
                if item.is_file():
                    item.unlink(missing_ok=True)
                    deleted_count += 1
                    logger.info(f"Janitor menghapus file temp: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_count += 1
                    logger.info(f"Janitor menghapus direktori temp: {item.name}")
        except Exception as e:
            logger.warning(f"Janitor gagal menghapus {item.name}: {e}")

    return deleted_count


def cleanup_expired_history() -> int:
    """
    Menghapus riwayat konversi dari database yang sudah melewati batas waktu expires_at.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        deleted = (
            db.query(ConversionHistory)
            .filter(ConversionHistory.expires_at < now)
            .delete()
        )
        if deleted > 0:
            db.commit()
            logger.info(f"Janitor membersihkan {deleted} riwayat konversi kadaluarsa (> 24 jam).")
        return deleted
    except Exception as e:
        logger.error(f"Gagal membersihkan riwayat kadaluarsa: {e}")
        return 0
    finally:
        db.close()


async def start_janitor_loop(
    temp_dir: Path | str = "temp",
    interval_seconds: int = 600,
    max_age_seconds: int = 1800,
) -> None:
    """
    Loop asinkron yang berjalan di background selama aplikasi FastAPI hidup.
    """
    logger.info("Background Janitor aktif (File temp & Database History cleaner).")
    while True:
        try:
            # 1. Bersihkan file temp lama
            cleanup_temp_files(temp_dir=temp_dir, max_age_seconds=max_age_seconds)
            # 2. Bersihkan riwayat database yang expired
            cleanup_expired_history()
        except Exception as e:
            logger.error(f"Error pada loop Janitor: {e}")

        await asyncio.sleep(interval_seconds)