"""Synthetic fixtures; SQLite is injected only into unit tests."""

import hashlib
import time
from unittest.mock import MagicMock

import pytest
import redis
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Account, Base, LoginSession, get_db, get_engine
from app.demo import hash_password, throttle_login, verify_password
from app.main import app
from app.seed_demo import main, seed_demo


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setenv("INFIRMO_DEMO_MODE", "true")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_demo(db)
        db.add(
            Account(
                email="other@infirmo.example",
                password_hash=hash_password("Other-demo-2026!"),
                display_name="Autre Démo",
                role="titulaire",
                city="Metz",
            )
        )
        db.commit()

    def session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[throttle_login] = lambda: None
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def sign_in(client, email="demo@infirmo.example", password="Infirmo-demo-2026!"):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.headers["cache-control"] == "no-store"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_profile_persists_across_sessions_and_is_isolated(demo):
    client, engine = demo
    auth = sign_in(client)
    profile = {"display_name": "  Alex Démo  ", "role": "titulaire", "city": "Toul"}
    response = client.put("/api/profile", headers=auth, json=profile)
    assert response.status_code == 200
    assert response.json() == {**profile, "display_name": "Alex Démo"}
    assert client.post("/api/auth/logout", headers=auth).status_code == 204
    assert client.get("/api/profile", headers=auth).status_code == 401
    assert client.get("/api/profile", headers=sign_in(client)).json()["city"] == "Toul"
    other = sign_in(client, "other@infirmo.example", "Other-demo-2026!")
    assert client.get("/api/profile", headers=other).json()["city"] == "Metz"
    with Session(engine) as db:
        seed_demo(db)
        assert (
            db.scalar(
                select(Account).where(Account.email == "demo@infirmo.example")
            ).city
            == "Toul"
        )
        stored = db.scalars(select(LoginSession)).all()
        assert all(len(item.token_hash) == 64 for item in stored)
        assert all(item.token_hash not in other["Authorization"] for item in stored)


@pytest.mark.parametrize(
    "path,method",
    [("/api/profile", "get"), ("/api/profile", "put"), ("/api/auth/logout", "post")],
)
def test_requires_authentication(demo, path, method):
    client, _ = demo
    kwargs = (
        {"json": {"display_name": "Démo", "city": "Nancy", "role": "titulaire"}}
        if method == "put"
        else {}
    )
    assert getattr(client, method)(path, **kwargs).status_code == 401
    assert (
        getattr(client, method)(
            path, headers={"Authorization": "Bearer invalid"}, **kwargs
        ).status_code
        == 401
    )


def test_expired_and_oversized_tokens_rejected(demo):
    client, engine = demo
    auth = sign_in(client)
    with Session(engine) as db:
        token_hash = hashlib.sha256(
            auth["Authorization"].split()[1].encode()
        ).hexdigest()
        db.get(LoginSession, token_hash).expires_at = int(time.time()) - 1
        db.commit()
    assert client.get("/api/profile", headers=auth).status_code == 401
    assert (
        client.get(
            "/api/profile", headers={"Authorization": "Bearer " + "a" * 129}
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "email,password",
    [("demo@infirmo.example", "incorrect"), ("unknown@infirmo.example", "incorrect")],
)
def test_generic_login_errors(demo, email, password):
    response = demo[0].post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize(
    "patch",
    [
        {"role": "admin"},
        {"city": " "},
        {"display_name": "a" * 81},
        {"id": "another-user"},
        {"city": "hello\nworld"},
    ],
)
def test_invalid_profile_does_not_write_or_echo_input(demo, patch):
    client, _ = demo
    auth = sign_in(client)
    before = client.get("/api/profile", headers=auth).json()
    response = client.put("/api/profile", headers=auth, json={**before, **patch})
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request"}
    assert client.get("/api/profile", headers=auth).json() == before


def test_invalid_login_does_not_echo_password(demo):
    response = demo[0].post(
        "/api/auth/login", json={"email": "invalid", "password": "sensitive-test-input"}
    )
    assert response.status_code == 422
    assert "sensitive-test-input" not in response.text


@pytest.mark.parametrize("mode", [None, "false", "TRUE"])
def test_demo_is_disabled_unless_explicit(monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv("INFIRMO_DEMO_MODE", raising=False)
    else:
        monkeypatch.setenv("INFIRMO_DEMO_MODE", mode)
    with TestClient(app) as client:
        assert client.get("/api/profile").status_code == 404
        assert (
            client.post(
                "/api/auth/login",
                json={"email": "demo@infirmo.example", "password": "x"},
            ).status_code
            == 404
        )
    with pytest.raises(SystemExit, match="Seed refused"):
        main()


def test_password_salts_and_verification():
    first = hash_password("synthetic-password")
    assert first != hash_password("synthetic-password")
    assert verify_password("synthetic-password", first)
    assert not verify_password("wrong-password", first)


def test_seed_rejects_non_synthetic_address(demo, monkeypatch):
    monkeypatch.setenv("INFIRMO_DEMO_EMAIL", "nurse@real-domain.fr")
    with Session(demo[1]) as db, pytest.raises(ValueError, match=".example"):
        seed_demo(db)


def test_runtime_rejects_sqlite(monkeypatch):
    get_engine.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    with pytest.raises(ValueError, match="PostgreSQL required"):
        get_engine()


def test_missing_database_configuration_is_generic(monkeypatch):
    get_engine.cache_clear()
    monkeypatch.setenv("INFIRMO_DEMO_MODE", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get(
            "/api/profile", headers={"Authorization": "Bearer invalid"}
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}


def test_database_errors_do_not_echo_parameters(demo):
    def unavailable():
        raise OperationalError(
            "query", {"secret": "synthetic-sensitive-value"}, Exception("private")
        )

    app.dependency_overrides[get_db] = unavailable
    response = demo[0].get("/api/profile", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}


def test_redis_throttle_and_outage(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    client = MagicMock()
    pipeline = (
        client.__enter__.return_value.pipeline.return_value.__enter__.return_value
    )
    pipeline.incr.return_value.expire.return_value.execute.return_value = [30, True]
    monkeypatch.setattr("app.demo.redis.from_url", lambda *args, **kwargs: client)
    throttle_login()
    pipeline.incr.return_value.expire.return_value.execute.return_value = [31, True]
    with pytest.raises(HTTPException) as error:
        throttle_login()
    assert error.value.status_code == 429
    pipeline.incr.return_value.expire.return_value.execute.side_effect = (
        redis.ConnectionError("must not be exposed")
    )
    with pytest.raises(HTTPException) as error:
        throttle_login()
    assert error.value.status_code == 503
    assert error.value.detail == "Service unavailable"
