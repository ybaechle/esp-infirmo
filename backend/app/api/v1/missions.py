import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import func, select

from app.api.deps import DB, require_role
from app.api.v1.applications import ApplicationPublic
from app.api.v1.offers import OfferPublic, member_offer
from app.errors import ApiError
from app.models import Application, Offer, User
from app.pagination import Page, Pagination
from app.services import notifications
from app.services.missions import next_status
from app.timeutil import as_utc, utcnow

router = APIRouter(tags=["missions"])
Titulaire = Annotated[User, Depends(require_role("titulaire"))]
Remplacant = Annotated[User, Depends(require_role("remplacant"))]


class StatusAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["start", "complete", "cancel"]


class Mission(BaseModel):
    offer: OfferPublic
    application: ApplicationPublic


@router.post("/offers/{offer_id}/status", response_model=OfferPublic)
def change_status(offer_id: uuid.UUID, body: StatusAction, user: Titulaire, db: DB):
    member_offer(db, offer_id, user)
    offer = db.scalar(select(Offer).where(Offer.id == offer_id).with_for_update())
    target = next_status(offer.status, body.action)
    if body.action == "start" and as_utc(offer.start_at) > utcnow():
        raise ApiError(409, "too_early", "The mission has not started yet")
    offer.status = target
    db.commit()
    hired = db.scalars(
        select(Application.user_id).where(
            Application.offer_id == offer.id, Application.status == "accepted"
        )
    ).all()
    notifications.notify(db, hired, "mission.status", offer_id=offer.id, status=target)
    return offer


@router.post("/applications/{application_id}/resign", response_model=OfferPublic)
def resign(application_id: uuid.UUID, user: Remplacant, db: DB):
    """Le remplaçant retenu se désiste avant le début : l'offre redevient disponible."""
    application = db.get(Application, application_id)
    if application is None or application.user_id != user.id:
        raise ApiError(404, "application_not_found", "Application not found")
    offer = db.scalar(
        select(Offer).where(Offer.id == application.offer_id).with_for_update()
    )
    if application.status != "accepted" or offer.status != "filled":
        raise ApiError(
            409, "cannot_resign", "Only an accepted, not yet started mission"
        )
    application.status, application.decided_at = "withdrawn", utcnow()
    offer.status = "open" if as_utc(offer.valid_till) > utcnow() else "cancelled"
    db.commit()
    notifications.notify(
        db,
        notifications.office_titulaires(db, offer.office_id),
        "mission.status",
        offer_id=offer.id,
        status=offer.status,
    )
    return offer


@router.get("/me/missions", response_model=Page[Mission])
def my_missions(
    user: Remplacant,
    db: DB,
    page: Pagination,
    start_after: AwareDatetime | None = None,
    end_before: AwareDatetime | None = None,
):
    statement = (
        select(Application, Offer)
        .join(Offer, Offer.id == Application.offer_id)
        .where(
            Application.user_id == user.id,
            Application.status == "accepted",
            Offer.status.in_(("filled", "in_progress", "completed")),
        )
    )
    if start_after:
        statement = statement.where(Offer.end_at > start_after)
    if end_before:
        statement = statement.where(Offer.start_at < end_before)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.execute(
        statement.order_by(Offer.start_at, Offer.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return Page(
        items=[
            Mission(
                offer=OfferPublic.model_validate(offer),
                application=ApplicationPublic.model_validate(application),
            )
            for application, offer in rows
        ],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
