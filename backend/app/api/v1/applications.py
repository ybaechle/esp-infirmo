import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser, require_role
from app.api.v1.offers import OfferPublic, member_offer
from app.api.v1.profile import CarePublic
from app.errors import ApiError
from app.models import Application, Offer, OfficeMember, Profile, User
from app.pagination import Page, Pagination, paginate
from app.timeutil import as_utc, utcnow

router = APIRouter(tags=["applications"])
Remplacant = Annotated[User, Depends(require_role("remplacant"))]
Titulaire = Annotated[User, Depends(require_role("titulaire"))]


class ApplyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str | None = Field(default=None, max_length=500)


class DecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["accepted", "rejected"]


class ApplicationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    status: str
    message: str | None
    created_at: datetime
    decided_at: datetime | None


class CandidatePublic(ApplicationPublic):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    city: str | None
    cares: list[CarePublic]


class MyApplication(ApplicationPublic):
    offer: OfferPublic


def candidate_view(application: Application, user: User, profile: Profile | None):
    return CandidatePublic.model_validate(
        {
            **ApplicationPublic.model_validate(application).model_dump(),
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "city": profile.city if profile else None,
            "cares": [CarePublic.model_validate(c) for c in profile.cares]
            if profile
            else [],
        }
    )


@router.post(
    "/offers/{offer_id}/applications", response_model=ApplicationPublic, status_code=201
)
def apply(offer_id: uuid.UUID, body: ApplyInput, user: Remplacant, db: DB):
    offer = db.get(Offer, offer_id)
    belongs = (
        offer is not None
        and db.get(OfficeMember, (offer.office_id, user.id)) is not None
    )
    if offer is None or belongs:
        raise ApiError(404, "offer_not_found", "Offer not found")
    if offer.status != "open" or as_utc(offer.valid_till) <= utcnow():
        raise ApiError(409, "offer_closed", "Offer is no longer open")
    application = Application(offer_id=offer.id, user_id=user.id, message=body.message)
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(
            409, "already_applied", "Already applied to this offer"
        ) from None
    return application


@router.get("/offers/{offer_id}/applications", response_model=Page[CandidatePublic])
def list_candidates(
    offer_id: uuid.UUID,
    user: Titulaire,
    db: DB,
    page: Pagination,
    status: Annotated[
        str | None, Query(pattern="^(pending|accepted|rejected|withdrawn)$")
    ] = None,
):
    member_offer(db, offer_id, user)
    statement = select(Application).where(Application.offer_id == offer_id)
    if status:
        statement = statement.where(Application.status == status)
    result = paginate(
        db, statement.order_by(Application.created_at, Application.id), page
    )
    result.items = [
        candidate_view(a, db.get(User, a.user_id), db.get(Profile, a.user_id))
        for a in result.items
    ]
    return result


@router.patch(
    "/offers/{offer_id}/applications/{application_id}", response_model=ApplicationPublic
)
def decide(
    offer_id: uuid.UUID,
    application_id: uuid.UUID,
    body: DecisionInput,
    user: Titulaire,
    db: DB,
):
    member_offer(db, offer_id, user)
    # Le verrou sérialise deux acceptations simultanées ; FOR UPDATE relit l'état à jour de l'offre.
    offer = db.scalar(select(Offer).where(Offer.id == offer_id).with_for_update())
    application = db.get(Application, application_id)
    if application is None or application.offer_id != offer_id:
        raise ApiError(404, "application_not_found", "Application not found")
    if application.status != "pending":
        raise ApiError(409, "already_decided", "Application already decided")
    if body.decision == "accepted":
        if offer.status != "open":
            raise ApiError(409, "offer_closed", "Offer is no longer open")
        offer.status = "filled"
        db.execute(
            update(Application)
            .where(
                Application.offer_id == offer_id,
                Application.id != application_id,
                Application.status == "pending",
            )
            .values(status="rejected", decided_at=utcnow(), decided_by=user.id)
        )
    application.status = body.decision
    application.decided_at, application.decided_by = utcnow(), user.id
    db.commit()
    return application


@router.delete("/applications/{application_id}", status_code=204)
def withdraw(application_id: uuid.UUID, user: Remplacant, db: DB):
    application = db.get(Application, application_id)
    if application is None or application.user_id != user.id:
        raise ApiError(404, "application_not_found", "Application not found")
    if application.status != "pending":
        raise ApiError(409, "not_pending", "Only pending applications can be withdrawn")
    application.status = "withdrawn"
    application.decided_at = utcnow()
    db.commit()


@router.get("/me/applications", response_model=Page[MyApplication])
def my_applications(user: CurrentUser, db: DB, page: Pagination):
    result = paginate(
        db,
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.created_at.desc(), Application.id),
        page,
    )
    result.items = [
        MyApplication.model_validate(
            {
                **ApplicationPublic.model_validate(a).model_dump(),
                "offer": OfferPublic.model_validate(db.get(Offer, a.offer_id)),
            }
        )
        for a in result.items
    ]
    return result
