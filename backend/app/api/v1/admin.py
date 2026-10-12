import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DB, AdminUser
from app.api.v1.auth import UserPublic
from app.errors import ApiError
from app.models import User
from app.pagination import Page, Pagination, paginate

router = APIRouter(prefix="/admin", tags=["admin"])


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "suspended"]


@router.get("/users", response_model=Page[UserPublic])
def list_users(admin: AdminUser, db: DB, page: Pagination):
    return paginate(db, select(User).order_by(User.created_at, User.id), page)


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user_status(
    user_id: uuid.UUID, body: StatusUpdate, admin: AdminUser, db: DB
):
    if user_id == admin.id:
        raise ApiError(409, "cannot_change_self", "Cannot change your own status")
    user = db.get(User, user_id)
    if user is None or user.status == "deleted":
        raise ApiError(404, "user_not_found", "User not found")
    user.status = body.status
    db.commit()
    return user
