import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.passwords import hash_password
from app.services.ordre import OrdreUnavailable, OrdreVerifier, get_ordre_verifier

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(get_db)]
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
