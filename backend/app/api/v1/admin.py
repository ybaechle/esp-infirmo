import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DB, AdminUser
from app.api.v1.auth import UserPublic
from app.errors import ApiError
from app.api.v1.documents import DocumentPublic
from app.models import AuditLog, Document, User
from app.pagination import Page, Pagination, paginate
from app.services import audit

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
    audit.record(db, admin.id, "admin.user_status", "user", user.id)
    db.commit()
    return user


class DocumentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected"]


@router.get("/documents", response_model=Page[DocumentPublic])
def list_pending_documents(admin: AdminUser, db: DB, page: Pagination):
    return paginate(
        db,
        select(Document)
        .where(Document.status == "pending")
        .order_by(Document.created_at, Document.id),
        page,
    )


@router.patch("/documents/{document_id}", response_model=DocumentPublic)
def review_document(
    document_id: uuid.UUID, body: DocumentReview, admin: AdminUser, db: DB
):
    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "document_not_found", "Document not found")
    document.status, document.reviewed_by = body.status, admin.id
    audit.record(db, admin.id, "admin.document_review", "document", document.id)
    db.commit()
    return document


class AuditPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    at: datetime
    actor_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    outcome: str


@router.get("/audit-logs", response_model=Page[AuditPublic])
def audit_logs(
    admin: AdminUser,
    db: DB,
    page: Pagination,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    since: AwareDatetime | None = None,
    until: AwareDatetime | None = None,
):
    statement = select(AuditLog)
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if since:
        statement = statement.where(AuditLog.at >= since)
    if until:
        statement = statement.where(AuditLog.at < until)
    return paginate(db, statement.order_by(AuditLog.at.desc(), AuditLog.id), page)
