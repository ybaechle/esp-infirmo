import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.timeutil import utcnow


class AuditLog(Base):
    """Trace d'un accès ou d'une modification sensible. Aucun contenu, aucune donnée personnelle."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'denied', 'failure')", name="ck_audit_logs_outcome"
        ),
        Index("ix_audit_logs_at", "at"),
        Index("ix_audit_logs_actor_at", "actor_id", "at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Pas de clé étrangère : la trace survit à la suppression du compte.
    actor_id: Mapped[uuid.UUID | None]
    action: Mapped[str] = mapped_column(String(40))
    resource_type: Mapped[str | None] = mapped_column(String(30))
    resource_id: Mapped[uuid.UUID | None]
    outcome: Mapped[str] = mapped_column(String(10), default="success")
