import json

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.errors import ApiError
from app.models import (
    Application,
    Availability,
    Conversation,
    Document,
    Message,
    OfficeMember,
    Profile,
)
from app.passwords import verify_password
from app.services import accounts, audit

router = APIRouter(prefix="/me", tags=["account"])


class DeleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


@router.delete("", status_code=204)
def delete_account(body: DeleteInput, user: CurrentUser, db: DB):
    if not verify_password(body.password, user.password_hash):
        raise ApiError(401, "invalid_credentials", "Invalid credentials")
    accounts.ensure_deletable(db, user)
    accounts.forget(db, user)


def iso(value):
    return value.isoformat() if value else None


@router.get("/export")
def export_data(user: CurrentUser, db: DB):
    """Portabilité : tout ce que la personne a fourni, dans un JSON lisible."""
    profile = db.get(Profile, user.id)
    conversations = select(Conversation.id).where(
        (Conversation.user_a == user.id) | (Conversation.user_b == user.id)
    )
    payload = {
        "account": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "phone": user.phone,
            "created_at": iso(user.created_at),
            "consented_at": iso(user.consented_at),
        },
        "profile": profile
        and {
            "city": profile.city,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "radius_km": profile.radius_km,
            "min_turnover": profile.min_turnover,
            "bio": profile.bio,
            "cares": [c.code for c in profile.cares],
        },
        "availabilities": [
            {"start_at": iso(a.start_at), "end_at": iso(a.end_at)}
            for a in db.scalars(
                select(Availability).where(Availability.user_id == user.id)
            )
        ],
        "applications": [
            {"offer_id": str(a.offer_id), "status": a.status, "message": a.message}
            for a in db.scalars(
                select(Application).where(Application.user_id == user.id)
            )
        ],
        "offices": [
            {"office_id": str(m.office_id), "role": m.member_role}
            for m in db.scalars(
                select(OfficeMember).where(OfficeMember.user_id == user.id)
            )
        ],
        "documents": [
            {
                "doc_type": d.doc_type,
                "status": d.status,
                "uploaded_at": iso(d.created_at),
            }
            for d in db.scalars(select(Document).where(Document.user_id == user.id))
        ],
        "messages_sent": [
            {
                "conversation_id": str(m.conversation_id),
                "text": m.body,
                "at": iso(m.created_at),
            }
            for m in db.scalars(
                select(Message)
                .where(
                    Message.sender_id == user.id,
                    Message.conversation_id.in_(conversations),
                )
                .order_by(Message.created_at)
            )
        ],
    }
    audit.record_now(db, user.id, "account.export", "user", user.id)
    return Response(
        json.dumps(payload, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="infirmo-export.json"'},
    )
