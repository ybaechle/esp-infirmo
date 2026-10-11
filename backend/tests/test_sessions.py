import time

import pytest
from sqlalchemy import select, update

from app.models import AuthSession, User

from tests.test_register import PASSWORD, payload

EMAIL = "camille.demo@infirmo.example"


@pytest.fixture
def account(client):
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201


def login(client, password=PASSWORD):
    return client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": password}
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_a_token_pair_that_opens_the_session(client, account):
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    me = client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == EMAIL


def test_login_gives_the_same_error_for_bad_password_and_unknown_email(client, account):
    wrong = login(client, "Mauvais-mot-de-passe-1")
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@infirmo.example", "password": "x"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_is_refused_for_a_suspended_account(client, account, db):
    db.execute(update(User).values(status="suspended"))
    db.commit()

    response = login(client)

    assert response.status_code == 403
    assert response.json()["code"] == "account_inactive"


@pytest.mark.parametrize("header", [None, "Bearer inconnu", "Bearer " + "x" * 200])
def test_protected_route_rejects_missing_or_unknown_tokens(client, header):
    headers = {"Authorization": header} if header else {}

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_access_token_expires(client, account, db):
    token = login(client).json()["access_token"]
    db.execute(update(AuthSession).values(access_expires_at=int(time.time()) - 1))
    db.commit()

    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401


def test_suspending_an_account_cuts_existing_tokens(client, account, db):
    token = login(client).json()["access_token"]
    db.execute(update(User).values(status="suspended"))
    db.commit()

    assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 403


def test_refresh_rotates_the_pair_and_retires_the_old_access_token(client, account):
    first = login(client).json()

    second = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert second.status_code == 200
    new = second.json()
    assert new["refresh_token"] != first["refresh_token"]
    assert (
        client.get("/api/v1/auth/me", headers=bearer(first["access_token"])).status_code
        == 401
    )
    assert (
        client.get("/api/v1/auth/me", headers=bearer(new["access_token"])).status_code
        == 200
    )


def test_replaying_a_used_refresh_token_revokes_the_whole_family(client, account):
    first = login(client).json()
    new = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    ).json()

    replay = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert replay.status_code == 401
    assert replay.json()["code"] == "refresh_token_reused"
    assert (
        client.get("/api/v1/auth/me", headers=bearer(new["access_token"])).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": new["refresh_token"]}
        ).status_code
        == 401
    )


def test_refresh_rejects_unknown_and_expired_tokens(client, account, db):
    first = login(client).json()
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "inconnu"}
        ).status_code
        == 401
    )
    db.execute(update(AuthSession).values(refresh_expires_at=int(time.time()) - 1))
    db.commit()

    expired = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert expired.status_code == 401


def test_refresh_refuses_a_suspended_account_and_keeps_it_out(client, account, db):
    first = login(client).json()
    db.execute(update(User).values(status="suspended"))
    db.commit()

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )

    assert response.status_code == 401
    db.expire_all()
    assert db.scalar(select(AuthSession.rotated_at)) is None


def test_logout_revokes_access_and_refresh(client, account):
    tokens = login(client).json()

    out = client.post("/api/v1/auth/logout", headers=bearer(tokens["access_token"]))

    assert out.status_code == 204
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(tokens["access_token"])
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )


def test_login_cleans_up_expired_sessions(client, account, db):
    login(client)
    db.execute(update(AuthSession).values(refresh_expires_at=int(time.time()) - 1))
    db.commit()

    login(client)

    db.expire_all()
    assert len(db.scalars(select(AuthSession)).all()) == 1
