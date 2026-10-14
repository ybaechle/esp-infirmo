import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NursingOffice(Base):
    __tablename__ = "nursing_offices"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_offices_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_offices_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    siret: Mapped[str | None] = mapped_column(String(14), unique=True)
    address: Mapped[str] = mapped_column(String(200))
    postcode: Mapped[str] = mapped_column(String(5))
    city: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float]
    longitude: Mapped[float]


class OfficeMember(Base):
    __tablename__ = "office_members"
    __table_args__ = (
        CheckConstraint("member_role IN ('owner', 'member')", name="ck_members_role"),
    )

    office_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nursing_offices.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    member_role: Mapped[str] = mapped_column(String(10))
