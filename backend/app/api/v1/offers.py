import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, require_role
from app.api.v1.offices import membership
from app.api.v1.profile import CarePublic
from app.errors import ApiError
from app.models import Care, NursingOffice, Offer, User
from app.pagination import Page, Pagination, paginate
from app.timeutil import as_utc, utcnow

router = APIRouter(tags=["offers"])
Titulaire = Annotated[User, Depends(require_role("titulaire"))]


class OfferInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=2000)
    start_at: AwareDatetime
    end_at: AwareDatetime
    valid_till: AwareDatetime
    turnover: int = Field(ge=0, le=100_000)
    care_codes: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("description")
    @classmethod
    def no_control_characters(cls, value):
        if any(not c.isprintable() and c not in "\n\t" for c in value):
            raise ValueError("Invalid text")
        return value

    @model_validator(mode="after")
    def coherent_dates(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        if self.valid_till > self.start_at:
            raise ValueError("valid_till must not be after start_at")
        if self.valid_till <= utcnow():
            raise ValueError("valid_till must be in the future")
        return self


class OfferPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    office_id: uuid.UUID
    description: str
    start_at: datetime
    end_at: datetime
    valid_till: datetime
    turnover: int
    status: str
    cares: list[CarePublic]

    @computed_field
    @property
    def expired(self) -> bool:
        """Offre restée ouverte après sa date limite : plus candidatable, sans statut stocké."""
        return self.status == "open" and as_utc(self.valid_till) <= utcnow()


def resolve_cares(db, codes: list[str]) -> list[Care]:
    unique = set(codes)
    cares = (
        db.scalars(select(Care).where(Care.code.in_(unique))).all() if unique else []
    )
    if len(cares) != len(unique):
        raise ApiError(422, "unknown_care", "Unknown care type")
    return list(cares)


def member_offer(db, offer_id: uuid.UUID, user: User) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None or membership(db, offer.office_id, user.id) is None:
        raise ApiError(404, "offer_not_found", "Offer not found")
    return offer


@router.post("/offices/{office_id}/offers", response_model=OfferPublic, status_code=201)
def publish_offer(office_id: uuid.UUID, body: OfferInput, user: Titulaire, db: DB):
    if (
        db.get(NursingOffice, office_id) is None
        or membership(db, office_id, user.id) is None
    ):
        raise ApiError(404, "office_not_found", "Office not found")
    offer = Offer(
        office_id=office_id,
        created_by=user.id,
        cares=resolve_cares(db, body.care_codes),
        **body.model_dump(exclude={"care_codes"}),
    )
    db.add(offer)
    db.commit()
    return offer


@router.get("/offices/{office_id}/offers", response_model=Page[OfferPublic])
def list_office_offers(
    office_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
    page: Pagination,
    status: Annotated[
        str | None, Query(pattern="^(open|filled|in_progress|completed|cancelled)$")
    ] = None,
):
    if membership(db, office_id, user.id) is None:
        raise ApiError(404, "office_not_found", "Office not found")
    statement = select(Offer).where(Offer.office_id == office_id)
    if status:
        statement = statement.where(Offer.status == status)
    return paginate(db, statement.order_by(Offer.start_at.desc(), Offer.id), page)


@router.get("/offers/{offer_id}", response_model=OfferPublic)
def get_offer(offer_id: uuid.UUID, user: CurrentUser, db: DB):
    offer = db.get(Offer, offer_id)
    visible = offer is not None and (
        membership(db, offer.office_id, user.id) is not None
        or (
            user.role == "remplacant"
            and offer.status == "open"
            and as_utc(offer.valid_till) > utcnow()
        )
    )
    if not visible:
        raise ApiError(404, "offer_not_found", "Offer not found")
    return offer


@router.put("/offers/{offer_id}", response_model=OfferPublic)
def update_offer(offer_id: uuid.UUID, body: OfferInput, user: Titulaire, db: DB):
    offer = member_offer(db, offer_id, user)
    if offer.status != "open":
        raise ApiError(409, "offer_not_editable", "Only open offers can be edited")
    for field, value in body.model_dump(exclude={"care_codes"}).items():
        setattr(offer, field, value)
    offer.cares = resolve_cares(db, body.care_codes)
    db.commit()
    return offer
