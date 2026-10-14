import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser, require_role
from app.errors import ApiError
from app.models import NursingOffice, OfficeMember, User
from app.services.ordre import luhn_valid

router = APIRouter(prefix="/offices", tags=["offices"])


class OfficeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    siret: str | None = Field(default=None, pattern=r"^\d{14}$")
    address: str = Field(min_length=1, max_length=200)
    postcode: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("name", "address", "city")
    @classmethod
    def printable_text(cls, value):
        if not value.isprintable():
            raise ValueError("Invalid text")
        return value

    @field_validator("siret")
    @classmethod
    def siret_checksum(cls, value):
        if value is not None and not luhn_valid(value):
            raise ValueError("Invalid SIRET")
        return value


class OfficePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    siret: str | None
    address: str
    postcode: str
    city: str
    latitude: float
    longitude: float
    member_role: str | None = None


class MemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID


def membership(db, office_id, user_id) -> OfficeMember | None:
    return db.get(OfficeMember, (office_id, user_id))


def require_owner(db, office_id, user) -> NursingOffice:
    office = db.get(NursingOffice, office_id)
    member = membership(db, office_id, user.id) if office else None
    if office is None or member is None:
        raise ApiError(404, "office_not_found", "Office not found")
    if member.member_role != "owner":
        raise ApiError(403, "owner_required", "Office owner required")
    return office


def render(office: NursingOffice, member_role: str) -> OfficePublic:
    out = OfficePublic.model_validate(office)
    out.member_role = member_role
    return out


@router.post("", response_model=OfficePublic, status_code=201)
def create_office(
    body: OfficeInput, db: DB, user: User = Depends(require_role("titulaire"))
):
    office = NursingOffice(**body.model_dump())
    db.add(office)
    try:
        db.flush()
        db.add(OfficeMember(office_id=office.id, user_id=user.id, member_role="owner"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "siret_exists", "SIRET already registered") from None
    return render(office, "owner")


@router.get("", response_model=list[OfficePublic])
def my_offices(user: CurrentUser, db: DB):
    rows = db.execute(
        select(NursingOffice, OfficeMember.member_role)
        .join(OfficeMember, OfficeMember.office_id == NursingOffice.id)
        .where(OfficeMember.user_id == user.id)
        .order_by(NursingOffice.name, NursingOffice.id)
    ).all()
    return [render(office, role) for office, role in rows]


@router.get("/{office_id}", response_model=OfficePublic)
def get_office(office_id: uuid.UUID, user: CurrentUser, db: DB):
    member = membership(db, office_id, user.id)
    if member is None:
        raise ApiError(404, "office_not_found", "Office not found")
    return render(db.get(NursingOffice, office_id), member.member_role)


@router.put("/{office_id}", response_model=OfficePublic)
def update_office(office_id: uuid.UUID, body: OfficeInput, user: CurrentUser, db: DB):
    office = require_owner(db, office_id, user)
    for field, value in body.model_dump().items():
        setattr(office, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "siret_exists", "SIRET already registered") from None
    return render(office, "owner")


@router.post("/{office_id}/members", status_code=204)
def add_member(office_id: uuid.UUID, body: MemberInput, user: CurrentUser, db: DB):
    require_owner(db, office_id, user)
    target = db.get(User, body.user_id)
    if target is None or target.status != "active":
        raise ApiError(404, "user_not_found", "User not found")
    if membership(db, office_id, target.id):
        raise ApiError(409, "already_member", "Already a member")
    db.add(OfficeMember(office_id=office_id, user_id=target.id, member_role="member"))
    db.commit()


@router.delete("/{office_id}/members/{user_id}", status_code=204)
def remove_member(office_id: uuid.UUID, user_id: uuid.UUID, user: CurrentUser, db: DB):
    require_owner(db, office_id, user)
    member = membership(db, office_id, user_id)
    if member is None:
        raise ApiError(404, "member_not_found", "Member not found")
    if member.member_role == "owner":
        raise ApiError(409, "cannot_remove_owner", "Cannot remove the owner")
    db.delete(member)
    db.commit()
