import pytest
from sqlalchemy import select

from app.models import Profile, User

from tests.helpers import seed_cares
from tests.test_register import PASSWORD, payload

EMAIL = "camille.demo@infirmo.example"
FULL = {
    "first_name": "Camille",
    "last_name": "Démo",
    "city": "Nancy",
    "latitude": 48.6921,
    "longitude": 6.1844,
    "radius_km": 30,
    "min_turnover": 450,
    "bio": "Disponible en semaine.",
    "care_codes": ["injections", "pansements"],
}


@pytest.fixture
def auth(client, db):
    seed_cares(db, "injections", "pansements")
    client.post("/api/v1/auth/register", json=payload())
    tokens = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).json()
    return {"Authorization": "Bearer " + tokens["access_token"]}


def test_profile_requires_authentication(client):
    assert client.get("/api/v1/profile").status_code == 401
    assert client.put("/api/v1/profile", json=FULL).status_code == 401
    assert client.get("/api/v1/cares").status_code == 401


def test_new_account_has_an_empty_profile(client, auth):
    body = client.get("/api/v1/profile", headers=auth).json()

    assert body["first_name"] == "Camille" and body["role"] == "remplacant"
    assert body["city"] is None and body["cares"] == []


def test_put_profile_saves_and_get_reads_it_back(client, auth):
    saved = client.put("/api/v1/profile", json=FULL, headers=auth)

    assert saved.status_code == 200
    body = client.get("/api/v1/profile", headers=auth).json()
    assert body["radius_km"] == 30 and body["bio"] == "Disponible en semaine."
    assert sorted(c["code"] for c in body["cares"]) == ["injections", "pansements"]


def test_put_profile_replaces_previous_values(client, auth, db):
    client.put("/api/v1/profile", json=FULL, headers=auth)

    client.put(
        "/api/v1/profile",
        json={"first_name": "Cam", "last_name": "Démo", "care_codes": ["injections"]},
        headers=auth,
    )

    body = client.get("/api/v1/profile", headers=auth).json()
    assert body["first_name"] == "Cam" and body["city"] is None
    assert [c["code"] for c in body["cares"]] == ["injections"]
    assert db.scalar(select(User.first_name)) == "Cam"


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": 91},
        {"radius_km": 0},
        {"radius_km": 500},
        {"min_turnover": -1},
        {"latitude": None},
        {"bio": "x" * 1001},
        {"care_codes": ["injections"] * 21},
        {"city": "Nan\x00cy"},
        {"role": "titulaire"},
    ],
)
def test_put_profile_rejects_invalid_input(client, auth, overrides):
    response = client.put("/api/v1/profile", json={**FULL, **overrides}, headers=auth)

    assert response.status_code == 422


def test_put_profile_rejects_unknown_care_without_saving(client, auth, db):
    response = client.put(
        "/api/v1/profile", json={**FULL, "care_codes": ["magie"]}, headers=auth
    )

    assert response.status_code == 422 and response.json()["code"] == "unknown_care"
    assert db.scalar(select(Profile)) is None


def test_profiles_are_isolated_between_accounts(client, auth):
    client.put("/api/v1/profile", json=FULL, headers=auth)
    client.post(
        "/api/v1/auth/register",
        json=payload(email="autre@infirmo.example", order_number="98765432103"),
    )
    other = client.post(
        "/api/v1/auth/login",
        json={"email": "autre@infirmo.example", "password": PASSWORD},
    ).json()

    body = client.get(
        "/api/v1/profile", headers={"Authorization": "Bearer " + other["access_token"]}
    ).json()

    assert body["city"] is None and body["cares"] == []


def test_cares_reference_is_listed_sorted_by_label(client, auth):
    cares = client.get("/api/v1/cares", headers=auth).json()

    labels = [c["label"] for c in cares]
    assert labels == sorted(labels)
    assert {"injections", "pansements"} <= {c["code"] for c in cares}
