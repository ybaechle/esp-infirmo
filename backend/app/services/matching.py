"""Recherche et classement des offres pour un remplaçant (F2.1, F2.2).

Score de pertinence sur 100 = 35 % proximité, 30 % couverture des disponibilités,
20 % chiffre d'affaires, 15 % adéquation des soins. Le classement porte sur les
`MAX_CANDIDATES` offres les plus proches : au-delà, l'utilisateur doit restreindre ses filtres.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import exists, literal, select
from sqlalchemy.orm import Session, selectinload

from app.geo import distance, within
from app.models import (
    Application,
    Availability,
    NursingOffice,
    Offer,
    OfficeMember,
    Profile,
    User,
    offer_cares,
)
from app.timeutil import as_utc, utcnow

MAX_CANDIDATES = 300
TURNOVER_REFERENCE = 1000
W_DISTANCE, W_AVAILABILITY, W_TURNOVER, W_CARES = 0.35, 0.30, 0.20, 0.15


@dataclass
class Filters:
    lat: float | None = None
    lon: float | None = None
    radius_km: int | None = None
    min_turnover: int | None = None
    care_ids: tuple[int, ...] = ()
    window_start: datetime | None = None
    window_end: datetime | None = None


@dataclass
class Match:
    offer: Offer
    city: str
    distance_km: float | None
    score: int
    availability: float
    matched_cares: list[str]


def merge_windows(
    windows: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def coverage(
    start: datetime, end: datetime, merged: list[tuple[datetime, datetime]]
) -> float:
    """Part de l'offre couverte par les disponibilités déjà fusionnées (0 à 1)."""
    total = (end - start).total_seconds()
    covered = sum(
        max(0.0, (min(end, w_end) - max(start, w_start)).total_seconds())
        for w_start, w_end in merged
    )
    return min(covered / total, 1.0) if total > 0 else 0.0


def relevance(
    distance_km: float | None,
    radius_km: int | None,
    turnover: int,
    availability: float,
    care_overlap: float,
) -> int:
    proximity = (
        0.5
        if distance_km is None or not radius_km
        else max(0.0, 1 - distance_km / radius_km)
    )
    value = (
        W_DISTANCE * proximity
        + W_AVAILABILITY * availability
        + W_TURNOVER * min(turnover / TURNOVER_REFERENCE, 1.0)
        + W_CARES * care_overlap
    )
    return round(100 * value)


def search(db: Session, user: User, filters: Filters) -> list[Match]:
    profile = db.get(Profile, user.id)
    lat = (
        filters.lat
        if filters.lat is not None
        else (profile.latitude if profile else None)
    )
    lon = (
        filters.lon
        if filters.lon is not None
        else (profile.longitude if profile else None)
    )
    radius = filters.radius_km or (profile.radius_km if profile else None)
    min_turnover = filters.min_turnover
    if min_turnover is None and profile:
        min_turnover = profile.min_turnover
    geo = lat is not None and lon is not None
    radius = radius or 50

    now = utcnow()
    where = [
        Offer.status == "open",
        Offer.valid_till > now,
        ~exists().where(
            OfficeMember.office_id == Offer.office_id, OfficeMember.user_id == user.id
        ),
        ~exists().where(
            Application.offer_id == Offer.id, Application.user_id == user.id
        ),
    ]
    if filters.care_ids:
        where.append(
            Offer.id.in_(
                select(offer_cares.c.offer_id).where(
                    offer_cares.c.care_id.in_(filters.care_ids)
                )
            )
        )
    if min_turnover:
        where.append(Offer.turnover >= min_turnover)
    if filters.window_start:
        where.append(Offer.end_at > filters.window_start)
    if filters.window_end:
        where.append(Offer.start_at < filters.window_end)

    meters = (
        distance(NursingOffice.longitude, NursingOffice.latitude, lon, lat)
        if geo
        else literal(None)
    )
    if geo:
        where.append(
            within(
                NursingOffice.longitude, NursingOffice.latitude, lon, lat, radius * 1000
            )
        )
    rows = db.execute(
        select(Offer, NursingOffice.city, meters)
        .join(NursingOffice, NursingOffice.id == Offer.office_id)
        .options(selectinload(Offer.cares))
        .where(*where)
        .order_by(meters if geo else Offer.start_at, Offer.id)
        .limit(MAX_CANDIDATES)
    ).all()

    windows = merge_windows(
        [
            (as_utc(a.start_at), as_utc(a.end_at))
            for a in db.scalars(
                select(Availability).where(Availability.user_id == user.id)
            )
        ]
    )
    own_cares = {c.code for c in profile.cares} if profile else set()
    matches = []
    for offer, city, meters_away in rows:
        km = round(meters_away / 1000, 1) if meters_away is not None else None
        wanted = {c.code for c in offer.cares}
        overlap = len(wanted & own_cares) / len(wanted) if wanted and own_cares else 0.5
        covered = coverage(as_utc(offer.start_at), as_utc(offer.end_at), windows)
        matches.append(
            Match(
                offer=offer,
                city=city,
                distance_km=km,
                score=relevance(km, radius, offer.turnover, covered, overlap),
                availability=round(covered, 2),
                matched_cares=sorted(wanted & own_cares),
            )
        )
    return matches
