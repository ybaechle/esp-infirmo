"""Synthetic-only authentication. Not production healthcare authentication."""

import hashlib
import hmac
import os
import secrets
import time
from typing import Annotated, Literal

import redis
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import Account, LoginSession, get_db


def require_demo():
    if os.environ.get("INFIRMO_DEMO_MODE") != "true":
        raise HTTPException(404, "Not found")


router = APIRouter(prefix="/api", dependencies=[Depends(require_demo)])
DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


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


class Profile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, from_attributes=True
    )
    display_name: str = Field(min_length=1, max_length=80)
    role: Literal["titulaire", "remplacant"]
    city: str = Field(min_length=1, max_length=80)

    @field_validator("display_name", "city")
    @classmethod
    def printable_text(cls, value):
        if not value.isprintable():
            raise ValueError("Invalid text")
        return value


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    salt = bytes.fromhex(encoded.split(":", 1)[0])
    return hmac.compare_digest(hash_password(password, salt), encoded)


_DUMMY_HASH = hash_password("synthetic-unknown-account")


def throttle_login():
    # ponytail: 30 attempts/minute globally; use per-account/IP limits for a multi-user service.
    try:
        with redis.from_url(
            os.environ["REDIS_URL"], socket_timeout=2, socket_connect_timeout=2
        ) as client:
            with client.pipeline() as pipeline:
                key = f"infirmo:demo:login:{int(time.time()) // 60}"
                attempts, _ = pipeline.incr(key).expire(key, 120).execute()
    except (KeyError, ValueError, redis.RedisError):
        raise HTTPException(503, "Service unavailable") from None
    if attempts > 30:
        raise HTTPException(429, "Try again later", headers={"Retry-After": "60"})


@router.post("/auth/login", dependencies=[Depends(throttle_login)])
def login(body: LoginInput, db: DB):
    account = db.scalar(select(Account).where(Account.email == body.email))
    valid = verify_password(
        body.password, account.password_hash if account else _DUMMY_HASH
    )
    if not valid or account is None:
        raise HTTPException(401, "Invalid credentials")
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            account_id=account.id,
            expires_at=now + 3600,
        )
    )
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


def current_session(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if credentials is None or len(credentials.credentials) > 128:
        raise HTTPException(401, "Authentication required")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    session = db.get(LoginSession, token_hash)
    if session is None or session.expires_at <= int(time.time()):
        raise HTTPException(401, "Authentication required")
    return session


AuthSession = Annotated[LoginSession, Depends(current_session)]


@router.get("/profile", response_model=Profile)
def get_profile(session: AuthSession, db: DB):
    return db.get(Account, session.account_id)


@router.put("/profile", response_model=Profile)
def update_profile(body: Profile, session: AuthSession, db: DB):
    account = db.get(Account, session.account_id)
    for key, value in body.model_dump().items():
        setattr(account, key, value)
    db.commit()
    return account


@router.post("/auth/logout", status_code=204)
def logout(session: AuthSession, db: DB):
    db.delete(session)
    db.commit()
    return Response(status_code=204)
