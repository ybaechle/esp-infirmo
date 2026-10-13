import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TwoFactorChallenge(Base):
    """Code à usage unique envoyé par e-mail ou SMS ; seul son hachage est conservé."""

    __tablename__ = "two_factor_challenges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    purpose: Mapped[str] = mapped_column(String(10))
    channel: Mapped[str] = mapped_column(String(5))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int]
    attempts: Mapped[int] = mapped_column(default=0)
    consumed: Mapped[bool] = mapped_column(default=False)
