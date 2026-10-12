"""Limitation de débit par fenêtre fixe, partagée entre workers via Redis."""

import hashlib
import os
import time
from collections.abc import Callable
from typing import Annotated

import redis
from fastapi import Depends, Request

from app.errors import ApiError

Counter = Callable[[str, int], int]


def redis_counter(key: str, window: int) -> int:
    try:
        with redis.from_url(
            os.environ["REDIS_URL"], socket_timeout=2, socket_connect_timeout=2
        ) as client:
            with client.pipeline() as pipeline:
                count, _ = pipeline.incr(key).expire(key, window * 2).execute()
        return count
    except (KeyError, ValueError, redis.RedisError):
        # Fail closed : sans compteur, on ne laisse pas passer des tentatives illimitées.
        raise ApiError(503, "service_unavailable", "Service unavailable") from None


def get_counter() -> Counter:
    return redis_counter


class Throttle:
    def __init__(
        self, request: Request, counter: Annotated[Counter, Depends(get_counter)]
    ):
        self.ip = request.client.host if request.client else "unknown"
        self.counter = counter

    def check(self, scope: str, subject: str, max_attempts: int, window: int = 60):
        # Le sujet est haché : un email ne doit pas apparaître en clair dans Redis.
        digest = hashlib.sha256(subject.encode()).hexdigest()[:16]
        key = f"infirmo:rl:{scope}:{digest}:{int(time.time()) // window}"
        if self.counter(key, window) > max_attempts:
            raise ApiError(
                429,
                "too_many_attempts",
                "Try again later",
                {"Retry-After": str(window)},
            )


Limiter = Annotated[Throttle, Depends()]
