from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.user import User


def test_create_user_in_sqlite(tmp_path):
    # Buat database test sementara di memori/folder tmp
    test_db_file = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{test_db_file}")

    # Otomatis buat semua tabel (mirip CREATE TABLE IF NOT EXISTS)
    Base.metadata.create_all(bind=test_engine)

    TestingSession = sessionmaker(bind=test_engine)
    session = TestingSession()

    # Insert user baru (mirip INSERT INTO users ...)
    new_user = User(
        email="developer@file2md.local",
        hashed_password="dummy_hash_password",
        tier="free",
    )
    session.add(new_user)
    session.commit()

    # Query kembali user dari database (mirip SELECT * FROM users WHERE email = ...)
    saved_user = session.query(User).filter_by(email="developer@file2md.local").first()

    assert saved_user is not None
    assert saved_user.id == 1
    assert saved_user.tier == "free"
    assert saved_user.is_active is True

    session.close()