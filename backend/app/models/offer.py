import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.profile import Care

OFFER_STATUSES = ("open", "filled", "in_progress", "completed", "cancelled")

offer_cares = Table(
    "offer_cares",
    Base.metadata,
    Column("offer_id", ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True),
    Column("care_id", ForeignKey("cares.id", ondelete="CASCADE"), primary_key=True),
)


class Offer(Base):
    """Une tournée à remplacer ; son statut suit la mission (F3.4)."""

    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_offers_dates"),
        CheckConstraint("valid_till <= start_at", name="ck_offers_valid_till"),
        CheckConstraint("turnover >= 0", name="ck_offers_turnover"),
        CheckConstraint(
            "status IN ('open', 'filled', 'in_progress', 'completed', 'cancelled')",
            name="ck_offers_status",
        ),
        Index("ix_offers_status_start", "status", "start_at"),
        Index("ix_offers_office_id", "office_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nursing_offices.id", ondelete="CASCADE")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    description: Mapped[str] = mapped_column(String(2000))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_till: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    turnover: Mapped[int]
    status: Mapped[str] = mapped_column(String(12), default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cares: Mapped[list[Care]] = relationship(secondary=offer_cares)
