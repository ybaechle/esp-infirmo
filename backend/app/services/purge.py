"""Purge de rétention : à planifier (cron / tâche du compose), jamais déclenchée par une requête."""

import time
from datetime import timedelta

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.models import AuditLog, AuthSession, Transmission, TwoFactorChallenge
from app.timeutil import utcnow

AUDIT_RETENTION = timedelta(days=365)


def purge(db: Session) -> dict[str, int]:
    now, epoch = utcnow(), int(time.time())
    counts = {
        "transmissions": db.execute(
            delete(Transmission).where(Transmission.expires_at <= now)
        ).rowcount,
        "sessions": db.execute(
            delete(AuthSession).where(AuthSession.refresh_expires_at <= epoch)
        ).rowcount,
        "challenges": db.execute(
            delete(TwoFactorChallenge).where(
                or_(
                    TwoFactorChallenge.expires_at <= epoch,
                    TwoFactorChallenge.consumed.is_(True),
                )
            )
        ).rowcount,
        "audit_logs": db.execute(
            delete(AuditLog).where(AuditLog.at <= now - AUDIT_RETENTION)
        ).rowcount,
    }
    db.commit()
    return counts
