"""Explicit, idempotent bootstrap for a reserved-domain synthetic account."""

import os

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Account, get_engine
from app.demo import LoginInput, hash_password


def seed_demo(db: Session):
    if os.environ.get("INFIRMO_DEMO_MODE") != "true":
        raise ValueError("Seed refused: INFIRMO_DEMO_MODE must be true")
    credentials = LoginInput(
        email=os.environ.get("INFIRMO_DEMO_EMAIL", "demo@infirmo.example"),
        password=os.environ.get("INFIRMO_DEMO_PASSWORD", "Infirmo-demo-2026!"),
    )
    if not credentials.email.endswith(".example") or len(credentials.password) < 12:
        raise ValueError(
            "Seed requires a .example address and password of at least 12 characters"
        )
    if db.scalar(select(Account).where(Account.email == credentials.email)):
        return
    db.add(
        Account(
            email=credentials.email,
            password_hash=hash_password(credentials.password),
            display_name="Camille Démo",
            role="remplacant",
            city="Nancy",
        )
    )
    db.commit()


def main():
    if os.environ.get("INFIRMO_DEMO_MODE") != "true":
        raise SystemExit("Seed refused: INFIRMO_DEMO_MODE must be true")
    try:
        with Session(get_engine()) as db:
            seed_demo(db)
    except (KeyError, ValueError, SQLAlchemyError):
        raise SystemExit(
            "Seed failed: check demo configuration and database migrations"
        ) from None
    print("Synthetic demo account ready (existing profile preserved).")


if __name__ == "__main__":
    main()
