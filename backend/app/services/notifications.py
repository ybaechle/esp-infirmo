"""Création des alertes, diffusion temps réel et push éventuel (F2.5)."""

import logging
import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import realtime
from app.geo import haversine_km
from app.models import (
    DeviceToken,
    NursingOffice,
    Notification,
    Offer,
    OfficeMember,
    Profile,
    User,
)
from app.services import push

log = logging.getLogger(__name__)

PUSH_TEXTS = {
    "offer.match": ("Nouvelle offre", "Une offre correspond à votre profil."),
    "application.received": (
        "Nouvelle candidature",
        "Un remplaçant a candidaté à votre offre.",
    ),
    "application.decided": ("Candidature traitée", "Une réponse est disponible."),
    "mission.status": ("Mission mise à jour", "Le statut d'une mission a changé."),
}
MAX_RECIPIENTS = 500
DEFAULT_RADIUS_KM = 50


def notify(db: Session, user_ids: Iterable[uuid.UUID], type_: str, **data) -> None:
    """À appeler après la validation de l'action : l'alerte ne doit jamais précéder son effet."""
    recipients = list(dict.fromkeys(user_ids))
    if not recipients:
        return
    payload = {key: str(value) for key, value in data.items()}
    db.add_all(
        Notification(user_id=uid, type=type_, data=payload) for uid in recipients
    )
    db.commit()
    realtime.publish(
        recipients, {"type": "notification.new", "notification_type": type_, **payload}
    )
    sender = push.get_push_sender()
    if sender is None:
        return
    title, body = PUSH_TEXTS[type_]
    for token in db.scalars(
        select(DeviceToken).where(DeviceToken.user_id.in_(recipients))
    ):
        try:
            sender.send(token.platform, token.token, title, body)
        except (
            Exception
        ) as error:  # un fournisseur défaillant ne doit pas faire échouer l'action
            log.warning("push delivery failed: %s", type(error).__name__)


def office_titulaires(db: Session, office_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(User.id)
            .join(OfficeMember, OfficeMember.user_id == User.id)
            .where(
                OfficeMember.office_id == office_id,
                User.role == "titulaire",
                User.status == "active",
            )
        )
    )


def matching_substitutes(db: Session, offer: Offer) -> list[uuid.UUID]:
    """Remplaçants dont la zone, les soins et le CA minimum correspondent à l'offre."""
    office = db.get(NursingOffice, offer.office_id)
    wanted = {c.code for c in offer.cares}
    members = select(OfficeMember.user_id).where(
        OfficeMember.office_id == offer.office_id
    )
    rows = db.execute(
        select(Profile, User.id)
        .join(User, User.id == Profile.user_id)
        .where(
            User.role == "remplacant",
            User.status == "active",
            User.id.not_in(members),
            Profile.latitude.is_not(None),
            # Fenêtre large (rayon max 200 km) avant le calcul exact de distance.
            Profile.latitude.between(office.latitude - 2.5, office.latitude + 2.5),
            Profile.longitude.between(office.longitude - 4, office.longitude + 4),
        )
        .limit(MAX_RECIPIENTS * 4)
    ).all()
    matched = []
    for profile, user_id in rows:
        radius = profile.radius_km or DEFAULT_RADIUS_KM
        if (
            haversine_km(
                profile.latitude, profile.longitude, office.latitude, office.longitude
            )
            > radius
        ):
            continue
        if profile.min_turnover and offer.turnover < profile.min_turnover:
            continue
        own = {c.code for c in profile.cares}
        if wanted and own and not wanted & own:
            continue
        matched.append(user_id)
    return matched[:MAX_RECIPIENTS]
