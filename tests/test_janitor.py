import os
import time
from pathlib import Path
from app.services.janitor import cleanup_temp_files


def test_cleanup_temp_files_deletes_old_files(tmp_path: Path):
    # 1. Buat file lama (> 30 menit / 1800 detik yang lalu)
    old_file = tmp_path / "old_temp.txt"
    old_file.write_text("file lama")
    past_time = time.time() - 2000
    os.utime(old_file, (past_time, past_time))

    # 2. Buat file baru (< 30 menit)
    new_file = tmp_path / "new_temp.txt"
    new_file.write_text("file baru")

    # Jalankan cleanup dengan threshold 1800 detik
    deleted = cleanup_temp_files(temp_dir=tmp_path, max_age_seconds=1800)

    # Verifikasi
    assert deleted == 1
    assert not old_file.exists(), "File lama seharusnya terhapus"
    assert new_file.exists(), "File baru tidak boleh terhapus"


def test_cleanup_nonexistent_directory():
    # Folder tidak ada tidak boleh menyebabkan exception
    deleted = cleanup_temp_files(temp_dir="non_existent_folder_xyz")
    assert deleted == 0