from unittest.mock import MagicMock

import pytest
import redis

from app.errors import ApiError
from app.ratelimit import redis_counter

from tests.test_register import PASSWORD, payload

EMAIL = "camille.demo@infirmo.example"


def attempt(client, password="Mauvais-mot-de-passe-1"):
    return client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": password}
    )


def test_login_is_throttled_per_account_after_five_attempts(client):
    client.post("/api/v1/auth/register", json=payload())

    statuses = [attempt(client).status_code for _ in range(5)]
    blocked = attempt(client, PASSWORD)

    assert statuses == [401] * 5
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "too_many_attempts"
    assert blocked.headers["retry-after"] == "60"


def test_throttle_does_not_store_the_email_in_clear(client, counts):
    attempt(client)

    assert counts and all(EMAIL not in key for key in counts)


def test_register_is_throttled_per_ip_after_ten_attempts(client):
    codes = [
        client.post(
            "/api/v1/auth/register", json=payload(order_number="12345678904")
        ).status_code
        for _ in range(11)
    ]

    assert codes == [422] * 10 + [429]


def test_redis_counter_counts_and_fails_closed(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    client = MagicMock()
    pipeline = (
        client.__enter__.return_value.pipeline.return_value.__enter__.return_value
    )
    pipeline.incr.return_value.expire.return_value.execute.return_value = [7, True]
    monkeypatch.setattr("app.ratelimit.redis.from_url", lambda *a, **k: client)

    assert redis_counter("k", 60) == 7

    pipeline.incr.return_value.expire.return_value.execute.side_effect = (
        redis.ConnectionError("must not be exposed")
    )
    with pytest.raises(ApiError) as error:
        redis_counter("k", 60)
    assert error.value.status_code == 503
    assert "exposed" not in error.value.detail


def test_redis_counter_without_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ApiError) as error:
        redis_counter("k", 60)

    assert error.value.status_code == 503
