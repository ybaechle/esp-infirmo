"""PostgreSQL persistence for the synthetic demonstration."""

import os
import uuid
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import CheckConstraint, ForeignKey, String, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "demo_accounts"
    __table_args__ = (CheckConstraint("role IN ('titulaire', 'remplacant')"),)

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(80))


class LoginSession(Base):
    __tablename__ = "demo_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("demo_accounts.id", ondelete="CASCADE")
    )
    expires_at: Mapped[int]


@lru_cache(maxsize=1)
def get_engine():
    url = make_url(os.environ["DATABASE_URL"])
    if url.get_backend_name() != "postgresql":
        raise ValueError("PostgreSQL required; SQLite is restricted to tests")
    return create_engine(
        url.set(drivername="postgresql+psycopg"),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 2},
    )


def get_db():
    try:
        engine = get_engine()
    except (KeyError, ValueError):
        raise HTTPException(503, "Service unavailable") from None
    with Session(engine) as db:
        yield db
