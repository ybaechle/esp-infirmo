"""Émission, rotation et révocation des jetons opaques."""

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import AuthSession, User

ACCESS_TTL = 15 * 60
REFRESH_TTL = 7 * 24 * 3600


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int = ACCESS_TTL
    token_type: str = "bearer"


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue(db: Session, user_id: uuid.UUID, family_id: uuid.UUID | None = None):
    now = int(time.time())
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            access_hash=digest(access),
            refresh_hash=digest(refresh),
            access_expires_at=now + ACCESS_TTL,
            refresh_expires_at=now + REFRESH_TTL,
        )
    )
    return TokenPair(access, refresh)


def purge_expired(db: Session):
    db.execute(
        delete(AuthSession).where(AuthSession.refresh_expires_at <= int(time.time()))
    )


def _revoke_family(db: Session, family_id: uuid.UUID):
    db.execute(
        update(AuthSession)
        .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=int(time.time()))
    )


def _reject_reuse(db: Session, session: AuthSession):
    # Un refresh déjà échangé qui revient est le signe d'un jeton volé.
    _revoke_family(db, session.family_id)
    db.commit()
    raise ApiError(401, "refresh_token_reused", "Refresh token already used")


def rotate(db: Session, refresh_token: str) -> TokenPair:
    now = int(time.time())
    session = db.scalar(
        select(AuthSession).where(AuthSession.refresh_hash == digest(refresh_token))
    )
    if session is None or session.refresh_expires_at <= now:
        raise ApiError(401, "invalid_refresh_token", "Invalid refresh token")
    if session.rotated_at is not None:
        return _reject_reuse(db, session)
    if session.revoked_at is not None:
        raise ApiError(401, "invalid_refresh_token", "Invalid refresh token")
    claimed = db.execute(
        update(AuthSession)
        .where(AuthSession.id == session.id, AuthSession.rotated_at.is_(None))
        .values(rotated_at=now, revoked_at=now)
    )
    if claimed.rowcount != 1:
        return _reject_reuse(db, session)
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        db.rollback()
        raise ApiError(401, "invalid_refresh_token", "Invalid refresh token")
    pair = issue(db, session.user_id, session.family_id)
    db.commit()
    return pair


def revoke_family_of(db: Session, session: AuthSession):
    _revoke_family(db, session.family_id)
    db.commit()
