import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.api.deps import require_role
from app.main import app
from app.models import User

from tests.test_register import PASSWORD, payload


def sign_up(client, email, order, role="remplacant"):
    assert (
        client.post(
            "/api/v1/auth/register",
            json=payload(email=email, order_number=order, role=role),
        ).status_code
        == 201
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()
    return {"Authorization": "Bearer " + tokens["access_token"]}


@pytest.fixture
def admin(client, db):
    headers = sign_up(client, "admin@infirmo.example", "12345678903", "titulaire")
    db.execute(
        update(User).where(User.email == "admin@infirmo.example").values(is_admin=True)
    )
    db.commit()
    return headers


@pytest.fixture
def member(client):
    return sign_up(client, "membre@infirmo.example", "98765432103")


def test_admin_routes_require_the_admin_flag(client, member):
    assert client.get("/api/v1/admin/users").status_code == 401
    forbidden = client.get("/api/v1/admin/users", headers=member)

    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "admin_required"


def test_admin_lists_users_with_pagination(client, admin, member):
    page = client.get("/api/v1/admin/users", params={"limit": 1}, headers=admin).json()

    assert page["total"] == 2 and len(page["items"]) == 1
    assert "password_hash" not in str(page)


def test_admin_suspends_then_reactivates_an_account(client, admin, member):
    target = next(
        u
        for u in client.get("/api/v1/admin/users", headers=admin).json()["items"]
        if u["email"] == "membre@infirmo.example"
    )

    suspended = client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"status": "suspended"},
        headers=admin,
    )
    assert suspended.status_code == 200
    assert client.get("/api/v1/auth/me", headers=member).status_code == 403

    client.patch(
        f"/api/v1/admin/users/{target['id']}", json={"status": "active"}, headers=admin
    )
    assert client.get("/api/v1/auth/me", headers=member).status_code == 200


def test_admin_cannot_suspend_self_or_unknown_users(client, admin):
    me = client.get("/api/v1/auth/me", headers=admin).json()

    own = client.patch(
        f"/api/v1/admin/users/{me['id']}", json={"status": "suspended"}, headers=admin
    )
    unknown = client.patch(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000",
        json={"status": "suspended"},
        headers=admin,
    )

    assert own.status_code == 409 and own.json()["code"] == "cannot_change_self"
    assert unknown.status_code == 404


def test_admin_rejects_invalid_status(client, admin):
    me = client.get("/api/v1/auth/me", headers=admin).json()

    response = client.patch(
        f"/api/v1/admin/users/{me['id']}", json={"status": "deleted"}, headers=admin
    )

    assert response.status_code == 422


def test_require_role_allows_only_listed_roles(client, db_engine):
    probe = FastAPI()
    probe.dependency_overrides = app.dependency_overrides
    probe.exception_handlers.update(app.exception_handlers)

    @probe.get("/titulaire-only", dependencies=[Depends(require_role("titulaire"))])
    def titulaire_only():
        return {"ok": True}

    holder = sign_up(client, "titulaire@infirmo.example", "12345678903", "titulaire")
    replacement = sign_up(client, "remplacant@infirmo.example", "98765432103")
    probe_client = TestClient(probe)

    assert probe_client.get("/titulaire-only", headers=holder).status_code == 200
    denied = probe_client.get("/titulaire-only", headers=replacement)
    assert denied.status_code == 403 and denied.json()["code"] == "forbidden_role"
