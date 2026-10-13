import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

profile_cares = Table(
    "profile_cares",
    Base.metadata,
    Column(
        "user_id", ForeignKey("profiles.user_id", ondelete="CASCADE"), primary_key=True
    ),
    Column("care_id", ForeignKey("cares.id", ondelete="CASCADE"), primary_key=True),
)


class Care(Base):
    """Référentiel des types de soins, partagé par les compétences et les offres."""

    __tablename__ = "cares"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    label: Mapped[str] = mapped_column(String(80))


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_profiles_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_profiles_longitude"),
        CheckConstraint("radius_km BETWEEN 1 AND 200", name="ck_profiles_radius"),
        CheckConstraint("min_turnover >= 0", name="ck_profiles_min_turnover"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    city: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    radius_km: Mapped[int | None]
    min_turnover: Mapped[int | None]
    bio: Mapped[str | None] = mapped_column(String(1000))
    cares: Mapped[list[Care]] = relationship(secondary=profile_cares)
