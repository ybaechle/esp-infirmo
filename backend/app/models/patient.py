import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.crypto import EncryptedText
from app.database import Base
from app.timeutil import utcnow


class Patient(Base):
    """Dossier minimal d'un patient d'un cabinet ; identité chiffrée, effacée à l'anonymisation."""

    __tablename__ = "patients"
    __table_args__ = (Index("ix_patients_office_id", "office_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    office_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nursing_offices.id", ondelete="CASCADE")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    first_name: Mapped[str | None] = mapped_column(EncryptedText("patients.first_name"))
    last_name: Mapped[str | None] = mapped_column(EncryptedText("patients.last_name"))
    birth_date: Mapped[str | None] = mapped_column(EncryptedText("patients.birth_date"))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Transmission(Base):
    __tablename__ = "transmissions"
    __table_args__ = (
        Index("ix_transmissions_patient_created", "patient_id", "created_at"),
        Index("ix_transmissions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE")
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    text: Mapped[str] = mapped_column(EncryptedText("transmissions.text"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
