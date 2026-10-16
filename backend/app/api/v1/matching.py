import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, require_role
from app.api.v1.offers import OfferPublic
from app.errors import ApiError
from app.models import Availability, Care, User
from app.pagination import Page, Pagination, paginate
from app.services import matching

router = APIRouter(tags=["matching"])
Remplacant = Annotated[User, Depends(require_role("remplacant"))]
SORTS = {
    "relevance": lambda m: (-m.score, m.offer.start_at, str(m.offer.id)),
    "distance": lambda m: (m.distance_km is None, m.distance_km or 0, str(m.offer.id)),
    "turnover": lambda m: (-m.offer.turnover, str(m.offer.id)),
    "date": lambda m: (m.offer.start_at, str(m.offer.id)),
}


class OfferMatch(OfferPublic):
    city: str
    distance_km: float | None
    score: int
    availability: float
    matched_cares: list[str]


@router.get("/offers/search", response_model=Page[OfferMatch])
def search_offers(
    user: Remplacant,
    db: DB,
    page: Pagination,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_km: Annotated[int | None, Query(ge=1, le=200)] = None,
    min_turnover: Annotated[int | None, Query(ge=0)] = None,
    care: Annotated[list[str] | None, Query(max_length=20)] = None,
    window_start: AwareDatetime | None = None,
    window_end: AwareDatetime | None = None,
    sort: Literal["relevance", "distance", "turnover", "date"] = "relevance",
):
    if (lat is None) != (lon is None):
        raise ApiError(422, "coordinates_incomplete", "lat and lon go together")
    care_ids: tuple[int, ...] = ()
    if care:
        rows = db.scalars(select(Care).where(Care.code.in_(set(care)))).all()
        if len(rows) != len(set(care)):
            raise ApiError(422, "unknown_care", "Unknown care type")
        care_ids = tuple(c.id for c in rows)
    found = matching.search(
        db,
        user,
        matching.Filters(
            lat, lon, radius_km, min_turnover, care_ids, window_start, window_end
        ),
    )
    found.sort(key=SORTS[sort])
    window = found[page.offset : page.offset + page.limit]
    return Page(
        items=[
            OfferMatch.model_validate(
                {
                    **OfferPublic.model_validate(m.offer).model_dump(),
                    "city": m.city,
                    "distance_km": m.distance_km,
                    "score": m.score,
                    "availability": m.availability,
                    "matched_cares": m.matched_cares,
                }
            )
            for m in window
        ],
        total=len(found),
        limit=page.limit,
        offset=page.offset,
    )


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode="after")
    def coherent(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        if (self.end_at - self.start_at).days > 366:
            raise ValueError("window too long")
        return self


class AvailabilityPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_at: datetime
    end_at: datetime


@router.post("/availabilities", response_model=AvailabilityPublic, status_code=201)
def add_availability(body: AvailabilityInput, user: Remplacant, db: DB):
    availability = Availability(user_id=user.id, **body.model_dump())
    db.add(availability)
    db.commit()
    return availability


@router.get("/availabilities", response_model=Page[AvailabilityPublic])
def list_availabilities(user: Remplacant, db: DB, page: Pagination):
    return paginate(
        db,
        select(Availability)
        .where(Availability.user_id == user.id)
        .order_by(Availability.start_at, Availability.id),
        page,
    )


@router.delete("/availabilities/{availability_id}", status_code=204)
def delete_availability(availability_id: uuid.UUID, user: CurrentUser, db: DB):
    availability = db.get(Availability, availability_id)
    if availability is None or availability.user_id != user.id:
        raise ApiError(404, "availability_not_found", "Availability not found")
    db.delete(availability)
    db.commit()
