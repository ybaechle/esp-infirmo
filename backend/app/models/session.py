import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuthSession(Base):
    """Une paire access/refresh ; seuls les SHA-256 des jetons sont conservés."""

    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_family_id", "family_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    family_id: Mapped[uuid.UUID]
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires_at: Mapped[int]
    refresh_expires_at: Mapped[int]
    rotated_at: Mapped[int | None]
    revoked_at: Mapped[int | None]
