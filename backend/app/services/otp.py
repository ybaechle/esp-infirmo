"""Codes à usage unique pour la 2FA (F1.4).

Aucun fournisseur d'e-mail ou de SMS n'est branché : en introduire un impose une revue de
résidence des données et un contrat de sous-traitance (AGENTS.md). `OtpSender` est le point
d'ancrage de cette intégration ; sans elle, l'envoi échoue explicitement.
"""

import hashlib
import hmac
import secrets
import time
import uuid
from typing import Protocol

from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import TwoFactorChallenge, User

CODE_TTL = 5 * 60
MAX_ATTEMPTS = 5


class OtpUnavailable(Exception):
    """Aucun fournisseur d'envoi n'est configuré, ou il n'a pas répondu."""


class OtpSender(Protocol):
    def send(self, channel: str, destination: str, code: str) -> None: ...


class UnconfiguredSender:
    def send(self, channel: str, destination: str, code: str) -> None:
        raise OtpUnavailable


def get_otp_sender() -> OtpSender:
    return UnconfiguredSender()


def _digest(challenge_id: uuid.UUID, code: str) -> str:
    return hashlib.sha256(f"{challenge_id}:{code}".encode()).hexdigest()


def destination_for(user: User, channel: str) -> str:
    destination = user.email if channel == "email" else user.phone
    if not destination:
        raise ApiError(422, "phone_required", "A phone number is required for SMS")
    return destination


def start_challenge(
    db: Session, user: User, purpose: str, channel: str, sender: OtpSender
) -> uuid.UUID:
    destination = destination_for(user, channel)
    challenge_id = uuid.uuid4()
    code = f"{secrets.randbelow(10**6):06d}"
    try:
        sender.send(channel, destination, code)
    except OtpUnavailable:
        raise ApiError(503, "otp_unavailable", "Code delivery unavailable") from None
    db.add(
        TwoFactorChallenge(
            id=challenge_id,
            user_id=user.id,
            purpose=purpose,
            channel=channel,
            code_hash=_digest(challenge_id, code),
            expires_at=int(time.time()) + CODE_TTL,
        )
    )
    db.commit()
    return challenge_id


def check_challenge(
    db: Session, challenge_id: uuid.UUID, code: str, purpose: str, user_id=None
) -> TwoFactorChallenge:
    challenge = db.get(TwoFactorChallenge, challenge_id)
    if (
        challenge is None
        or challenge.purpose != purpose
        or challenge.consumed
        or challenge.expires_at <= int(time.time())
        or (user_id is not None and challenge.user_id != user_id)
    ):
        raise ApiError(401, "invalid_code", "Invalid or expired code")
    challenge.attempts += 1
    if challenge.attempts > MAX_ATTEMPTS:
        challenge.consumed = True
        db.commit()
        raise ApiError(401, "invalid_code", "Invalid or expired code")
    if not hmac.compare_digest(challenge.code_hash, _digest(challenge_id, code)):
        db.commit()
        raise ApiError(401, "invalid_code", "Invalid or expired code")
    challenge.consumed = True
    db.commit()
    return challenge
