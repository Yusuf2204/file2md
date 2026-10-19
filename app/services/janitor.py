import asyncio
import logging
import time
from pathlib import Path

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
        if item.is_file():
            try:
                # Periksa waktu modifikasi terakhir file
                file_age = now - item.stat().st_mtime
                if file_age > max_age_seconds:
                    item.unlink(missing_ok=True)
                    deleted_count += 1
                    logger.info(f"Janitor menghapus file temp kadaluarsa: {item.name} (usia {int(file_age)}s)")
            except Exception as e:
                logger.warning(f"Janitor gagal menghapus file {item.name}: {e}")

    return deleted_count


async def start_janitor_loop(
    temp_dir: Path | str = "temp",
    interval_seconds: int = 600,
    max_age_seconds: int = 1800,
) -> None:
    """
    Loop asinkron yang berjalan di background selama aplikasi FastAPI hidup.
    """
    logger.info(
        f"Background Janitor aktif (Interval: {interval_seconds}s, Max Age: {max_age_seconds}s)"
    )
    while True:
        try:
            cleaned = cleanup_temp_files(temp_dir=temp_dir, max_age_seconds=max_age_seconds)
            if cleaned > 0:
                logger.info(f"Background Janitor selesai membersihkan {cleaned} file kadaluarsa.")
        except Exception as e:
            logger.error(f"Error pada loop Janitor: {e}")

        # Tidur secara non-blocking selama interval detik
        await asyncio.sleep(interval_seconds)