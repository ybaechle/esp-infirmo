import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app import realtime, storage
from app.api.deps import DB, CurrentUser
from app.errors import ApiError
from app.models import Application, Conversation, Message, Offer, OfficeMember, User
from app.pagination import Page, Pagination, paginate
from app.timeutil import utcnow

router = APIRouter(tags=["messages"])

MAX_PHOTO = 5 * 1024 * 1024
CHUNK = 64 * 1024
CONTEXT = b"messages.attachment"
SIGNATURES = {b"\xff\xd8\xff": "jpeg", b"\x89PNG\r\n\x1a\n": "png"}
MEDIA = {"jpeg": "image/jpeg", "png": "image/png"}


class OpenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID


class TextInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=4000)


class Peer(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class ConversationPublic(BaseModel):
    id: uuid.UUID
    peer: Peer
    last_message_at: datetime | None
    unread: int


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID
    text: str | None = Field(validation_alias="body")
    has_photo: bool = False
    created_at: datetime
    read_at: datetime | None


def pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return (a, b) if str(a) < str(b) else (b, a)


def are_connected(db, a: uuid.UUID, b: uuid.UUID) -> bool:
    """Même cabinet, ou l'un candidate à une offre du cabinet de l'autre."""
    mine, theirs = OfficeMember, OfficeMember.__table__.alias("theirs")
    shared = exists().where(
        mine.user_id == a, theirs.c.user_id == b, mine.office_id == theirs.c.office_id
    )

    def applied_to_office_of(candidate, member):
        return exists().where(
            Application.user_id == candidate,
            Application.offer_id == Offer.id,
            Offer.office_id == OfficeMember.office_id,
            OfficeMember.user_id == member,
        )

    return bool(
        db.scalar(
            select(or_(shared, applied_to_office_of(a, b), applied_to_office_of(b, a)))
        )
    )


def participant_conversation(
    db, conversation_id: uuid.UUID, user: User
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or user.id not in (
        conversation.user_a,
        conversation.user_b,
    ):
        raise ApiError(404, "conversation_not_found", "Conversation not found")
    return conversation


def render(db, conversation: Conversation, user: User) -> ConversationPublic:
    peer_id = (
        conversation.user_b if conversation.user_a == user.id else conversation.user_a
    )
    peer = db.get(User, peer_id)
    unread = db.scalar(
        select(func.count()).where(
            Message.conversation_id == conversation.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
    )
    return ConversationPublic(
        id=conversation.id,
        peer=Peer(id=peer.id, first_name=peer.first_name, last_name=peer.last_name),
        last_message_at=conversation.last_message_at,
        unread=unread,
    )


def message_view(message: Message) -> MessagePublic:
    out = MessagePublic.model_validate(message)
    out.has_photo = message.attachment_key is not None
    return out


@router.post("/conversations", response_model=ConversationPublic)
def open_conversation(body: OpenInput, response: Response, user: CurrentUser, db: DB):
    target = db.get(User, body.user_id)
    if target is None or target.status != "active" or target.id == user.id:
        raise ApiError(404, "user_not_found", "User not found")
    if not are_connected(db, user.id, target.id):
        raise ApiError(
            403, "not_connected", "No professional relationship with this user"
        )
    a, b = pair(user.id, target.id)
    conversation = db.scalar(
        select(Conversation).where(Conversation.user_a == a, Conversation.user_b == b)
    )
    if conversation is None:
        conversation = Conversation(user_a=a, user_b=b)
        db.add(conversation)
        try:
            db.commit()
            response.status_code = 201
        except IntegrityError:
            db.rollback()
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.user_a == a, Conversation.user_b == b
                )
            )
    return render(db, conversation, user)


@router.get("/conversations", response_model=Page[ConversationPublic])
def list_conversations(user: CurrentUser, db: DB, page: Pagination):
    result = paginate(
        db,
        select(Conversation)
        .where(or_(Conversation.user_a == user.id, Conversation.user_b == user.id))
        .order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.id),
        page,
    )
    result.items = [render(db, c, user) for c in result.items]
    return result


def store_message(
    db, conversation, user, text, attachment_key=None, attachment_type=None
):
    message = Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        body=text,
        attachment_key=attachment_key,
        attachment_type=attachment_type,
    )
    conversation.last_message_at = utcnow()
    db.add(message)
    try:
        db.commit()
    except Exception:
        if attachment_key:
            storage.delete(attachment_key)
        raise
    peer = (
        conversation.user_b if conversation.user_a == user.id else conversation.user_a
    )
    realtime.publish(
        [peer],
        {
            "type": "message.new",
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
        },
    )
    return message


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=201,
)
def send_message(
    conversation_id: uuid.UUID, body: TextInput, user: CurrentUser, db: DB
):
    conversation = participant_conversation(db, conversation_id, user)
    return message_view(store_message(db, conversation, user, body.text))


def read_image(upload: UploadFile) -> tuple[bytes, str]:
    data = bytearray()
    while chunk := upload.file.read(CHUNK):
        data.extend(chunk)
        if len(data) > MAX_PHOTO:
            raise ApiError(413, "file_too_large", "Photo exceeds 5 MB")
    for signature, kind in SIGNATURES.items():
        if data.startswith(signature):
            return bytes(data), kind
    raise ApiError(422, "not_an_image", "Only JPEG and PNG photos are accepted")


@router.post(
    "/conversations/{conversation_id}/photos",
    response_model=MessagePublic,
    status_code=201,
)
def send_photo(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: DB,
    file: Annotated[UploadFile, File()],
    text: Annotated[str | None, Form(max_length=4000)] = None,
    content_length: Annotated[int | None, Header()] = None,
):
    conversation = participant_conversation(db, conversation_id, user)
    if content_length is not None and content_length > MAX_PHOTO + CHUNK:
        raise ApiError(413, "file_too_large", "Photo exceeds 5 MB")
    data, kind = read_image(file)
    key = storage.put(data, CONTEXT)
    return message_view(store_message(db, conversation, user, text or None, key, kind))


@router.get(
    "/conversations/{conversation_id}/messages", response_model=Page[MessagePublic]
)
def list_messages(
    conversation_id: uuid.UUID, user: CurrentUser, db: DB, page: Pagination
):
    conversation = participant_conversation(db, conversation_id, user)
    result = paginate(
        db,
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id),
        page,
    )
    result.items = [message_view(m) for m in result.items]
    return result


@router.post("/conversations/{conversation_id}/read", status_code=204)
def mark_read(conversation_id: uuid.UUID, user: CurrentUser, db: DB):
    conversation = participant_conversation(db, conversation_id, user)
    db.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .values(read_at=utcnow())
    )
    db.commit()


@router.get("/messages/{message_id}/photo")
def download_photo(message_id: uuid.UUID, user: CurrentUser, db: DB):
    message = db.get(Message, message_id)
    conversation = db.get(Conversation, message.conversation_id) if message else None
    allowed = (
        conversation is not None
        and message.attachment_key is not None
        and user.id in (conversation.user_a, conversation.user_b)
    )
    if not allowed:
        raise ApiError(404, "photo_not_found", "Photo not found")
    return Response(
        storage.get(message.attachment_key, CONTEXT),
        media_type=MEDIA[message.attachment_type],
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
