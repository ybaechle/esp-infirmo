from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """SQLite relit les dates sans fuseau ; PostgreSQL les rend avec. Tout est en UTC ici."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
