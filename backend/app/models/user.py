import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

ROLES = ("titulaire", "remplacant")
STATUSES = ("active", "suspended", "deleted")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('titulaire', 'remplacant')", name="ck_users_role"),
        CheckConstraint(
            "status IN ('active', 'suspended', 'deleted')", name="ck_users_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20))
    order_number: Mapped[str] = mapped_column(String(11), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_admin: Mapped[bool] = mapped_column(default=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
