"""Droit à l'oubli et portabilité (F6.4)."""

import secrets
import uuid

from sqlalchemy import delete, exists, or_, select, update
from sqlalchemy.orm import Session

from app import storage
from app.errors import ApiError
from app.models import (
    Application,
    AuthSession,
    Availability,
    Conversation,
    Document,
    Message,
    Offer,
    OfficeMember,
    Profile,
    TwoFactorChallenge,
    User,
)
from app.passwords import hash_password
from app.services import audit

ACTIVE_MISSION = ("filled", "in_progress")


def ensure_deletable(db: Session, user: User) -> None:
    if user.is_admin:
        raise ApiError(
            409, "admin_cannot_delete", "Administrators cannot delete themselves"
        )
    as_substitute = exists().where(
        Application.user_id == user.id,
        Application.status == "accepted",
        Application.offer_id == Offer.id,
        Offer.status.in_(ACTIVE_MISSION),
    )
    as_owner = exists().where(
        OfficeMember.user_id == user.id,
        OfficeMember.member_role == "owner",
        Offer.office_id == OfficeMember.office_id,
        Offer.status.in_(("open", *ACTIVE_MISSION)),
    )
    if db.scalar(select(or_(as_substitute, as_owner))):
        raise ApiError(
            409, "active_missions", "Finish or cancel your missions and offers first"
        )


def forget(db: Session, user: User) -> None:
    """Efface ce qui identifie la personne ; l'historique des offres et décisions reste, anonymisé."""
    conversations = select(Conversation.id).where(
        or_(Conversation.user_a == user.id, Conversation.user_b == user.id)
    )
    files = [
        *db.scalars(select(Document.storage_key).where(Document.user_id == user.id)),
        *db.scalars(
            select(Message.attachment_key).where(
                Message.conversation_id.in_(conversations),
                Message.attachment_key.is_not(None),
            )
        ),
    ]
    db.execute(delete(Message).where(Message.conversation_id.in_(conversations)))
    db.execute(
        delete(Conversation).where(Conversation.id.in_(conversations.scalar_subquery()))
    )
    for model in (
        Document,
        Availability,
        Profile,
        OfficeMember,
        AuthSession,
        TwoFactorChallenge,
    ):
        db.execute(delete(model).where(model.user_id == user.id))
    db.execute(
        update(Application)
        .where(Application.user_id == user.id, Application.status == "pending")
        .values(status="withdrawn")
    )
    token = uuid.uuid4().hex
    user.email = f"deleted-{token}@deleted.invalid"
    user.first_name, user.last_name = "Compte", "Supprimé"
    user.phone = user.two_factor_channel = None
    user.order_number = "D" + token[:10]
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.status = "deleted"
    audit.record(db, user.id, "account.delete", "user", user.id)
    db.commit()
    for key in files:
        storage.delete(key)
