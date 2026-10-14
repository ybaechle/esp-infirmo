import pytest

from tests.helpers import ORDERS, sign_up, user_id

SIRET = "73282932000074"
OFFICE = {
    "name": "Cabinet des Lilas",
    "siret": SIRET,
    "address": "12 rue Stanislas",
    "postcode": "54000",
    "city": "Nancy",
    "latitude": 48.6937,
    "longitude": 6.1834,
}


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def stranger(client):
    return sign_up(client, "autre@infirmo.example", ORDERS[1], "titulaire")


@pytest.fixture
def substitute(client):
    return sign_up(client, "remplacant@infirmo.example", ORDERS[2])


def create(client, headers, **overrides):
    return client.post("/api/v1/offices", json={**OFFICE, **overrides}, headers=headers)


def test_siret_fixture_is_luhn_valid():
    from app.services.ordre import luhn_valid

    assert luhn_valid(SIRET)


def test_owner_creates_an_office_and_becomes_its_owner(client, owner):
    response = create(client, owner)

    assert response.status_code == 201
    assert response.json()["member_role"] == "owner"
    listed = client.get("/api/v1/offices", headers=owner).json()
    assert [o["name"] for o in listed] == ["Cabinet des Lilas"]


def test_only_titulaires_create_offices(client, substitute):
    response = create(client, substitute)

    assert response.status_code == 403 and response.json()["code"] == "forbidden_role"


@pytest.mark.parametrize(
    "overrides",
    [
        {"siret": "12345678901234"},
        {"siret": "123"},
        {"postcode": "5400"},
        {"latitude": 120},
        {"name": ""},
        {"unknown": 1},
    ],
)
def test_office_input_is_validated(client, owner, overrides):
    assert create(client, owner, **overrides).status_code == 422


def test_siret_must_be_unique(client, owner, stranger):
    create(client, owner)

    duplicate = create(client, stranger)

    assert duplicate.status_code == 409 and duplicate.json()["code"] == "siret_exists"


def test_non_members_cannot_see_an_office(client, owner, stranger):
    office = create(client, owner).json()

    assert (
        client.get(f"/api/v1/offices/{office['id']}", headers=stranger).status_code
        == 404
    )
    assert client.get("/api/v1/offices", headers=stranger).json() == []


def test_owner_updates_the_office_and_members_cannot(client, owner, substitute):
    office = create(client, owner).json()
    me = user_id(client, substitute)
    client.post(
        f"/api/v1/offices/{office['id']}/members", json={"user_id": me}, headers=owner
    )

    ok = client.put(
        f"/api/v1/offices/{office['id']}",
        json={**OFFICE, "city": "Metz"},
        headers=owner,
    )
    denied = client.put(
        f"/api/v1/offices/{office['id']}",
        json={**OFFICE, "city": "Toul"},
        headers=substitute,
    )

    assert ok.json()["city"] == "Metz"
    assert denied.status_code == 403 and denied.json()["code"] == "owner_required"


def test_owner_manages_members(client, owner, substitute):
    office = create(client, owner).json()
    me = user_id(client, substitute)
    url = f"/api/v1/offices/{office['id']}/members"

    assert client.post(url, json={"user_id": me}, headers=owner).status_code == 204
    again = client.post(url, json={"user_id": me}, headers=owner)
    assert again.status_code == 409 and again.json()["code"] == "already_member"
    seen = client.get(f"/api/v1/offices/{office['id']}", headers=substitute).json()
    assert seen["member_role"] == "member"

    assert client.delete(f"{url}/{me}", headers=owner).status_code == 204
    assert (
        client.get(f"/api/v1/offices/{office['id']}", headers=substitute).status_code
        == 404
    )
    assert client.delete(f"{url}/{me}", headers=owner).status_code == 404


def test_owner_cannot_be_removed_and_unknown_users_are_refused(client, owner):
    office = create(client, owner).json()
    url = f"/api/v1/offices/{office['id']}/members"

    removed = client.delete(f"{url}/{user_id(client, owner)}", headers=owner)
    unknown = client.post(
        url, json={"user_id": "00000000-0000-0000-0000-000000000000"}, headers=owner
    )

    assert (
        removed.status_code == 409 and removed.json()["code"] == "cannot_remove_owner"
    )
    assert unknown.status_code == 404


def test_members_cannot_add_members(client, owner, substitute, stranger):
    office = create(client, owner).json()
    url = f"/api/v1/offices/{office['id']}/members"
    client.post(url, json={"user_id": user_id(client, substitute)}, headers=owner)

    response = client.post(
        url, json={"user_id": user_id(client, stranger)}, headers=substitute
    )

    assert response.status_code == 403
