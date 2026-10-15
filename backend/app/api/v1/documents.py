import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Header, Response, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app import storage
from app.api.deps import DB, CurrentUser
from app.errors import ApiError
from app.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_SIZE = 5 * 1024 * 1024
CHUNK = 64 * 1024
CONTEXT = b"documents.file"


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doc_type: str
    status: str
    size: int
    created_at: datetime


def read_pdf(upload: UploadFile) -> bytes:
    """Lit par blocs et s'arrête dès que la limite est franchie ; le contenu fait foi, pas l'en-tête."""
    data = bytearray()
    while chunk := upload.file.read(CHUNK):
        data.extend(chunk)
        if len(data) > MAX_SIZE:
            raise ApiError(413, "file_too_large", "File exceeds 5 MB")
    if not data.startswith(b"%PDF-"):
        raise ApiError(422, "not_a_pdf", "Only PDF files are accepted")
    return bytes(data)


@router.post("", response_model=DocumentPublic, status_code=201)
def upload_document(
    user: CurrentUser,
    db: DB,
    doc_type: Annotated[Literal["carte_pro", "rib", "assurance"], Form()],
    file: Annotated[UploadFile, File()],
    content_length: Annotated[int | None, Header()] = None,
):
    if content_length is not None and content_length > MAX_SIZE + CHUNK:
        raise ApiError(413, "file_too_large", "File exceeds 5 MB")
    data = read_pdf(file)
    key = storage.put(data, CONTEXT)
    previous = db.scalar(
        select(Document).where(
            Document.user_id == user.id, Document.doc_type == doc_type
        )
    )
    old_key = previous.storage_key if previous else None
    document = previous or Document(user_id=user.id, doc_type=doc_type)
    document.storage_key, document.size = key, len(data)
    document.status, document.reviewed_by = "pending", None
    db.add(document)
    try:
        db.commit()
    except Exception:
        storage.delete(key)
        raise
    if old_key:
        storage.delete(old_key)
    return document


@router.get("", response_model=list[DocumentPublic])
def list_documents(user: CurrentUser, db: DB):
    return db.scalars(
        select(Document).where(Document.user_id == user.id).order_by(Document.doc_type)
    ).all()


def owned_or_admin(db, document_id: uuid.UUID, user) -> Document:
    document = db.get(Document, document_id)
    if document is None or (document.user_id != user.id and not user.is_admin):
        raise ApiError(404, "document_not_found", "Document not found")
    return document


@router.get("/{document_id}/file")
def download_document(document_id: uuid.UUID, user: CurrentUser, db: DB):
    document = owned_or_admin(db, document_id, user)
    return Response(
        storage.get(document.storage_key, CONTEXT),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document.doc_type}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, user: CurrentUser, db: DB):
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise ApiError(404, "document_not_found", "Document not found")
    key = document.storage_key
    db.delete(document)
    db.commit()
    storage.delete(key)
