import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DB, CurrentUser
from app.api.v1.auth import LoginOutput, _open_session
from app.errors import ApiError
from app.models import User
from app.passwords import verify_password
from app.ratelimit import Limiter
from app.services import audit, otp

router = APIRouter(prefix="/auth/2fa", tags=["auth"])
Sender = Annotated[otp.OtpSender, Depends(otp.get_otp_sender)]


class EnableInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["email", "sms"]
    phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")


class CodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: uuid.UUID
    code: str = Field(pattern=r"^\d{6}$")


class ChallengeOutput(BaseModel):
    challenge_id: uuid.UUID


class DisableInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


@router.post("/enable", response_model=ChallengeOutput, status_code=202)
def enable(body: EnableInput, user: CurrentUser, db: DB, sender: Sender):
    if body.phone:
        user.phone = body.phone
    return {
        "challenge_id": otp.start_challenge(db, user, "enable", body.channel, sender)
    }


@router.post("/confirm", status_code=204)
def confirm(body: CodeInput, user: CurrentUser, db: DB):
    challenge = otp.check_challenge(db, body.challenge_id, body.code, "enable", user.id)
    user.two_factor_channel = challenge.channel
    audit.record(db, user.id, "auth.2fa_enabled", "user", user.id)
    db.commit()


@router.post("/disable", status_code=204)
def disable(body: DisableInput, user: CurrentUser, db: DB):
    if not verify_password(body.password, user.password_hash):
        raise ApiError(401, "invalid_credentials", "Invalid credentials")
    user.two_factor_channel = None
    audit.record(db, user.id, "auth.2fa_disabled", "user", user.id)
    db.commit()


@router.post("/verify", response_model=LoginOutput)
def verify(body: CodeInput, db: DB, throttle: Limiter):
    throttle.check("2fa-ip", throttle.ip, 30)
    challenge = otp.check_challenge(db, body.challenge_id, body.code, "login")
    user = db.get(User, challenge.user_id)
    if user is None or user.status != "active":
        raise ApiError(403, "account_inactive", "Account inactive")
    return _open_session(db, user)
