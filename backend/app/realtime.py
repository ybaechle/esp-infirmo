"""Événements temps réel diffusés par Redis pub/sub (§10.3).

La diffusion est au mieux : l'API REST reste la source de vérité, un événement perdu
est rattrapé à la prochaine lecture. Un événement ne porte que des identifiants.
"""

import json
import logging
import os
from collections.abc import Iterable
from uuid import UUID

import redis

log = logging.getLogger(__name__)


def channel(user_id: UUID | str) -> str:
    return f"infirmo:events:{user_id}"


def publish(user_ids: Iterable[UUID], event: dict) -> None:
    payload = json.dumps(event)
    try:
        with redis.from_url(
            os.environ["REDIS_URL"], socket_timeout=2, socket_connect_timeout=2
        ) as client:
            for user_id in set(user_ids):
                client.publish(channel(user_id), payload)
    except (KeyError, ValueError, redis.RedisError) as error:
        log.warning("realtime publish failed: %s", type(error).__name__)
