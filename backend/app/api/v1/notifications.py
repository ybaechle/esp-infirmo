import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.errors import ApiError
from app.models import DeviceToken, Notification
from app.pagination import Page, Pagination, paginate
from app.timeutil import utcnow

router = APIRouter(tags=["notifications"])


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    data: dict
    created_at: datetime
    read_at: datetime | None


class DeviceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["android", "ios", "web"]
    token: Annotated[str, Field(min_length=8, max_length=255)]


@router.get("/notifications", response_model=Page[NotificationPublic])
def list_notifications(
    user: CurrentUser, db: DB, page: Pagination, unread_only: bool = False
):
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return paginate(
        db, statement.order_by(Notification.created_at.desc(), Notification.id), page
    )


@router.get("/notifications/unread-count")
def unread_count(user: CurrentUser, db: DB):
    return {
        "unread": db.scalar(
            select(func.count()).where(
                Notification.user_id == user.id, Notification.read_at.is_(None)
            )
        )
    }


@router.post("/notifications/read", status_code=204)
def read_all(user: CurrentUser, db: DB):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    db.commit()


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_one(notification_id: uuid.UUID, user: CurrentUser, db: DB):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise ApiError(404, "notification_not_found", "Notification not found")
    notification.read_at = notification.read_at or utcnow()
    db.commit()


@router.put("/devices", status_code=204)
def register_device(body: DeviceInput, user: CurrentUser, db: DB):
    """Un jeton appartient à l'appareil : s'il change de compte, il suit le dernier connecté."""
    device = db.scalar(select(DeviceToken).where(DeviceToken.token == body.token))
    if device is None:
        device = DeviceToken(token=body.token)
        db.add(device)
    device.user_id, device.platform = user.id, body.platform
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "device_conflict", "Device already registered") from None


@router.delete("/devices/{token}", status_code=204)
def unregister_device(token: str, user: CurrentUser, db: DB):
    device = db.scalar(
        select(DeviceToken).where(
            DeviceToken.token == token, DeviceToken.user_id == user.id
        )
    )
    if device is None:
        raise ApiError(404, "device_not_found", "Device not found")
    db.delete(device)
    db.commit()
