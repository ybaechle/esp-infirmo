import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, exists, select

from app.api.deps import DB, CurrentUser, require_role
from app.api.v1.offices import membership
from app.errors import ApiError
from app.models import Application, NursingOffice, Offer, Patient, Transmission, User
from app.pagination import Page, Pagination, paginate
from app.services import audit
from app.timeutil import utcnow

router = APIRouter(tags=["patients"])
Titulaire = Annotated[User, Depends(require_role("titulaire"))]

RETENTION = timedelta(days=30)


class PatientInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date
    consent: Literal[True]

    @field_validator("birth_date")
    @classmethod
    def not_in_the_future(cls, value):
        if value > date.today():
            raise ValueError("birth_date cannot be in the future")
        return value


class PatientPublic(BaseModel):
    id: uuid.UUID
    office_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    birth_date: str | None
    anonymized: bool
    created_at: datetime


class TransmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10_000)


class TransmissionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID
    text: str
    created_at: datetime
    expires_at: datetime


def patient_view(patient: Patient) -> PatientPublic:
    return PatientPublic(
        id=patient.id,
        office_id=patient.office_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        birth_date=patient.birth_date,
        anonymized=patient.anonymized_at is not None,
        created_at=patient.created_at,
    )


def is_retained_substitute(db, user: User, office_id: uuid.UUID) -> bool:
    """Remplaçant retenu sur une mission du cabinet, en cours ou encore dans la fenêtre de conservation."""
    cutoff = utcnow() - RETENTION
    return bool(
        db.scalar(
            select(
                exists().where(
                    Application.user_id == user.id,
                    Application.status == "accepted",
                    Application.offer_id == Offer.id,
                    Offer.office_id == office_id,
                    Offer.status.in_(("filled", "in_progress", "completed")),
                    Offer.end_at > cutoff,
                )
            )
        )
    )


def accessible_patient(db, patient_id: uuid.UUID, user: User) -> Patient:
    patient = db.get(Patient, patient_id)
    allowed = patient is not None and (
        membership(db, patient.office_id, user.id) is not None
        or (
            user.role == "remplacant"
            and is_retained_substitute(db, user, patient.office_id)
        )
    )
    if not allowed or patient.anonymized_at is not None:
        audit.record_now(db, user.id, "patient.access", "patient", patient_id, "denied")
        raise ApiError(404, "patient_not_found", "Patient not found")
    return patient


@router.post(
    "/offices/{office_id}/patients", response_model=PatientPublic, status_code=201
)
def create_patient(office_id: uuid.UUID, body: PatientInput, user: Titulaire, db: DB):
    if (
        db.get(NursingOffice, office_id) is None
        or membership(db, office_id, user.id) is None
    ):
        raise ApiError(404, "office_not_found", "Office not found")
    patient = Patient(
        office_id=office_id,
        created_by=user.id,
        first_name=body.first_name,
        last_name=body.last_name,
        birth_date=body.birth_date.isoformat(),
        consent_at=utcnow(),
    )
    db.add(patient)
    db.flush()
    audit.record(db, user.id, "patient.create", "patient", patient.id)
    db.commit()
    return patient_view(patient)


@router.get("/offices/{office_id}/patients", response_model=Page[PatientPublic])
def list_patients(office_id: uuid.UUID, user: Titulaire, db: DB, page: Pagination):
    if membership(db, office_id, user.id) is None:
        raise ApiError(404, "office_not_found", "Office not found")
    result = paginate(
        db,
        select(Patient)
        .where(Patient.office_id == office_id, Patient.anonymized_at.is_(None))
        .order_by(Patient.created_at, Patient.id),
        page,
    )
    result.items = [patient_view(p) for p in result.items]
    return result


@router.delete("/patients/{patient_id}", status_code=204)
def forget_patient(patient_id: uuid.UUID, user: Titulaire, db: DB):
    """Droit à l'oubli : identité effacée et transmissions supprimées, pas seulement masquées."""
    patient = accessible_patient(db, patient_id, user)
    db.execute(delete(Transmission).where(Transmission.patient_id == patient.id))
    patient.first_name = patient.last_name = patient.birth_date = None
    patient.anonymized_at = utcnow()
    audit.record(db, user.id, "patient.forget", "patient", patient.id)
    db.commit()


@router.post(
    "/patients/{patient_id}/transmissions",
    response_model=TransmissionPublic,
    status_code=201,
)
def add_transmission(
    patient_id: uuid.UUID, body: TransmissionInput, user: CurrentUser, db: DB
):
    patient = accessible_patient(db, patient_id, user)
    now = utcnow()
    transmission = Transmission(
        patient_id=patient.id,
        author_id=user.id,
        text=body.text,
        expires_at=now + RETENTION,
    )
    db.add(transmission)
    db.flush()
    audit.record(db, user.id, "transmission.create", "transmission", transmission.id)
    db.commit()
    return transmission


@router.get(
    "/patients/{patient_id}/transmissions", response_model=Page[TransmissionPublic]
)
def list_transmissions(
    patient_id: uuid.UUID, user: CurrentUser, db: DB, page: Pagination
):
    patient = accessible_patient(db, patient_id, user)
    audit.record_now(db, user.id, "transmission.read", "patient", patient.id)
    return paginate(
        db,
        select(Transmission)
        .where(
            Transmission.patient_id == patient.id, Transmission.expires_at > utcnow()
        )
        .order_by(Transmission.created_at.desc(), Transmission.id),
        page,
    )
