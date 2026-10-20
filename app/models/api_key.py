from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), default="Default Key", nullable=False)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)
    key_prefix = Column(String(32), nullable=False)  # Contoh: f2md_live_a1b2...9z8y
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} user_id={self.user_id} name={self.name}>"