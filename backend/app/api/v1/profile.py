from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.errors import ApiError
from app.models import Care, Profile

router = APIRouter(tags=["profile"])


class CarePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: int | None = Field(default=None, ge=1, le=200)
    min_turnover: int | None = Field(default=None, ge=0, le=1_000_000)
    bio: str | None = Field(default=None, max_length=1000)
    care_codes: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("first_name", "last_name", "city")
    @classmethod
    def printable_text(cls, value):
        if value is not None and not value.isprintable():
            raise ValueError("Invalid text")
        return value

    @model_validator(mode="after")
    def coordinates_come_together(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude go together")
        return self


class ProfileOutput(BaseModel):
    first_name: str
    last_name: str
    role: str
    city: str | None
    latitude: float | None
    longitude: float | None
    radius_km: int | None
    min_turnover: int | None
    bio: str | None
    cares: list[CarePublic]


def render(user, profile: Profile | None) -> ProfileOutput:
    return ProfileOutput(
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        city=profile.city if profile else None,
        latitude=profile.latitude if profile else None,
        longitude=profile.longitude if profile else None,
        radius_km=profile.radius_km if profile else None,
        min_turnover=profile.min_turnover if profile else None,
        bio=profile.bio if profile else None,
        cares=[CarePublic.model_validate(c) for c in profile.cares] if profile else [],
    )


@router.get("/cares", response_model=list[CarePublic])
def list_cares(user: CurrentUser, db: DB):
    return db.scalars(select(Care).order_by(Care.label)).all()


@router.get("/profile", response_model=ProfileOutput)
def get_profile(user: CurrentUser, db: DB):
    return render(user, db.get(Profile, user.id))


@router.put("/profile", response_model=ProfileOutput)
def put_profile(body: ProfileInput, user: CurrentUser, db: DB):
    codes = set(body.care_codes)
    cares = db.scalars(select(Care).where(Care.code.in_(codes))).all() if codes else []
    if len(cares) != len(codes):
        raise ApiError(422, "unknown_care", "Unknown care type")
    profile = db.get(Profile, user.id) or Profile(user_id=user.id)
    for field in ("city", "latitude", "longitude", "radius_km", "min_turnover", "bio"):
        setattr(profile, field, getattr(body, field))
    profile.cares = list(cares)
    user.first_name, user.last_name = body.first_name, body.last_name
    db.add(profile)
    db.commit()
    return render(user, profile)
