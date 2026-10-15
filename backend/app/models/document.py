import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DOC_TYPES = ("carte_pro", "rib", "assurance")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("user_id", "doc_type", name="uq_documents_user_type"),
        CheckConstraint(
            "doc_type IN ('carte_pro', 'rib', 'assurance')", name="ck_documents_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_documents_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    doc_type: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str] = mapped_column(String(32), unique=True)
    size: Mapped[int]
    status: Mapped[str] = mapped_column(String(10), default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
