"""`python -m app.promote_admin <email>` : désigne un administrateur parmi les comptes existants."""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import User
from app.services import audit


def promote(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or user.status != "active":
        raise SystemExit("No active account with this email")
    user.is_admin = True
    audit.record(db, None, "admin.promote", "user", user.id)
    db.commit()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.promote_admin <email>")
    with Session(get_engine()) as db:
        promote(db, sys.argv[1])


if __name__ == "__main__":
    main()
