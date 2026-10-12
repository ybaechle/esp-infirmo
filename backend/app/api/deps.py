import time
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import AuthSession, User
from app.services.sessions import digest

DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


def current_session(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> AuthSession:
    if credentials is None or len(credentials.credentials) > 128:
        raise ApiError(401, "authentication_required", "Authentication required")
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.access_hash == digest(credentials.credentials)
        )
    )
    if (
        session is None
        or session.revoked_at is not None
        or session.access_expires_at <= int(time.time())
    ):
        raise ApiError(401, "authentication_required", "Authentication required")
    return session


def current_user(db: DB, session: Annotated[AuthSession, Depends(current_session)]):
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise ApiError(403, "account_inactive", "Account inactive")
    return user


CurrentSession = Annotated[AuthSession, Depends(current_session)]
CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: str):
    def dependency(user: CurrentUser):
        if user.role not in roles:
            raise ApiError(403, "forbidden_role", "Role not allowed")
        return user

    return dependency


def require_admin(user: CurrentUser):
    if not user.is_admin:
        raise ApiError(403, "admin_required", "Administrator required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
