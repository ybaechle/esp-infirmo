import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentSession, CurrentUser
from app.errors import ApiError
from app.models import User
from app.passwords import DUMMY_HASH, hash_password, verify_password
from app.services import sessions
from app.services.ordre import OrdreUnavailable, OrdreVerifier, get_ordre_verifier

router = APIRouter(prefix="/auth", tags=["auth"])
Ordre = Annotated[OrdreVerifier, Depends(get_ordre_verifier)]


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=12, max_length=128)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    role: Literal["titulaire", "remplacant"]
    order_number: str = Field(pattern=r"^\d{11}$")
    accept_terms: Literal[True]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def printable_text(cls, value):
        if not value.isprintable():
            raise ValueError("Invalid text")
        return value


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    status: str


@router.post("/register", response_model=UserPublic, status_code=201)
def register(body: RegisterInput, db: DB, ordre: Ordre):
    try:
        order_ok = ordre.is_valid(body.order_number)
    except OrdreUnavailable:
        raise ApiError(
            503, "ordre_unavailable", "Order verification unavailable"
        ) from None
    if not order_ok:
        raise ApiError(422, "order_number_invalid", "Invalid order number")
    taken = db.scalar(
        select(User.id).where(
            (User.email == body.email) | (User.order_number == body.order_number)
        )
    )
    if taken:
        raise ApiError(409, "account_exists", "Account already exists")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        order_number=body.order_number,
        consented_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "account_exists", "Account already exists") from None
    return user


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class RefreshInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=128)


class TokenOutput(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


@router.post("/login", response_model=TokenOutput)
def login(body: LoginInput, db: DB):
    user = db.scalar(select(User).where(User.email == body.email))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not valid or user is None:
        raise ApiError(401, "invalid_credentials", "Invalid credentials")
    if user.status != "active":
        raise ApiError(403, "account_inactive", "Account inactive")
    sessions.purge_expired(db)
    pair = sessions.issue(db, user.id)
    db.commit()
    return asdict(pair)


@router.post("/refresh", response_model=TokenOutput)
def refresh(body: RefreshInput, db: DB):
    return asdict(sessions.rotate(db, body.refresh_token))


@router.post("/logout", status_code=204)
def logout(session: CurrentSession, db: DB):
    sessions.revoke_family_of(db, session)


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser):
    return user
