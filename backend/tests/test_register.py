import pytest
from sqlalchemy import select

from app.main import app
from app.models import User
from app.passwords import verify_password
from app.services.ordre import OrdreUnavailable, get_ordre_verifier, luhn_valid

VALID_ORDER = "12345678903"
PASSWORD = "Mot-de-passe-2026!"


def payload(**overrides):
    body = {
        "email": "Camille.Demo@Infirmo.example",
        "password": PASSWORD,
        "first_name": "Camille",
        "last_name": "Démo",
        "role": "remplacant",
        "order_number": VALID_ORDER,
        "accept_terms": True,
    }
    return {**body, **overrides}


def test_luhn_matches_the_rpps_check_digit():
    assert luhn_valid(VALID_ORDER)
    assert not luhn_valid("12345678904")


def test_register_creates_an_active_account_without_leaking_secrets(client, db):
    response = client.post("/api/v1/auth/register", json=payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "camille.demo@infirmo.example"
    assert body["status"] == "active"
    assert "password" not in response.text and "order_number" not in response.text
    user = db.scalar(select(User))
    assert verify_password(PASSWORD, user.password_hash)
    assert user.consented_at is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"accept_terms": False},
        {"password": "court"},
        {"role": "admin"},
        {"order_number": "123"},
        {"email": "pas-un-email"},
        {"first_name": "A\x00"},
        {"unknown": 1},
    ],
)
def test_register_rejects_invalid_input(client, overrides):
    assert (
        client.post("/api/v1/auth/register", json=payload(**overrides)).status_code
        == 422
    )


def test_register_rejects_an_order_number_that_fails_verification(client, db):
    response = client.post(
        "/api/v1/auth/register", json=payload(order_number="12345678904")
    )

    assert response.status_code == 422
    assert response.json()["code"] == "order_number_invalid"
    assert db.scalar(select(User)) is None


def test_register_refuses_duplicates_by_email_or_order_number(client):
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201

    same_email = client.post(
        "/api/v1/auth/register", json=payload(order_number="98765432103")
    )
    same_order = client.post(
        "/api/v1/auth/register", json=payload(email="autre@infirmo.example")
    )

    assert same_email.status_code == same_order.status_code == 409
    assert same_email.json()["code"] == "account_exists"


def test_register_fails_closed_when_order_service_is_down(client, db):
    class Down:
        def is_valid(self, order_number):
            raise OrdreUnavailable

    app.dependency_overrides[get_ordre_verifier] = lambda: Down()
    try:
        response = client.post("/api/v1/auth/register", json=payload())
    finally:
        app.dependency_overrides.pop(get_ordre_verifier)

    assert response.status_code == 503
    assert response.json()["code"] == "ordre_unavailable"
    assert db.scalar(select(User)) is None
