import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text, update

from app.models import Offer, Transmission
from tests.helpers import ORDERS, make_office, offer_payload, sign_up

PATIENT = {
    "first_name": "Jeanne",
    "last_name": "Dupont",
    "birth_date": "1948-03-12",
    "consent": True,
}


@pytest.fixture(autouse=True)
def keys(encryption_keys):
    return encryption_keys


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def office(client, owner):
    return make_office(client, owner)


@pytest.fixture
def patient(client, owner, office):
    response = client.post(
        f"/api/v1/offices/{office['id']}/patients", json=PATIENT, headers=owner
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def stranger(client):
    return sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")


def write(client, headers, patient, text_="Pansement refait, RAS."):
    return client.post(
        f"/api/v1/patients/{patient['id']}/transmissions",
        json={"text": text_},
        headers=headers,
    )


def hire(client, owner, office, db, status="filled"):
    """Un remplaçant retenu sur une mission du cabinet."""
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    application = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )
    return alice, offer


def test_patient_requires_explicit_consent_and_valid_data(client, owner, office):
    url = f"/api/v1/offices/{office['id']}/patients"
    for override in (
        {"consent": False},
        {"birth_date": "2999-01-01"},
        {"first_name": ""},
        {"unknown": 1},
    ):
        assert (
            client.post(url, json={**PATIENT, **override}, headers=owner).status_code
            == 422
        )
    no_consent = {k: v for k, v in PATIENT.items() if k != "consent"}
    assert client.post(url, json=no_consent, headers=owner).status_code == 422


def test_identity_is_encrypted_at_rest(client, patient, db):
    row = db.execute(
        text("SELECT first_name, last_name, birth_date FROM patients")
    ).one()

    assert all(value and "Dupont" not in value and "1948" not in value for value in row)
    assert patient["last_name"] == "Dupont"


def test_only_titulaires_of_the_office_manage_patients(
    client, owner, office, stranger, db
):
    url = f"/api/v1/offices/{office['id']}/patients"
    alice, _ = hire(client, owner, office, db)

    assert client.post(url, json=PATIENT, headers=stranger).status_code == 404
    assert client.post(url, json=PATIENT, headers=alice).status_code == 403
    assert client.get(url, headers=stranger).status_code == 404
    assert client.get(url, headers=alice).status_code == 403


def test_transmissions_are_stored_encrypted_and_listed_newest_first(
    client, owner, patient, db
):
    write(client, owner, patient, "première")
    write(client, owner, patient, "seconde")

    stored = db.execute(text("SELECT text FROM transmissions")).scalars().all()
    listing = client.get(
        f"/api/v1/patients/{patient['id']}/transmissions", headers=owner
    ).json()

    assert all("première" not in s and "seconde" not in s for s in stored)
    assert [t["text"] for t in listing["items"]] == ["seconde", "première"]


def test_transmission_input_is_validated(client, owner, patient):
    assert write(client, owner, patient, "").status_code == 422
    assert write(client, owner, patient, "x" * 10_001).status_code == 422


def test_outsiders_cannot_read_or_write_transmissions(client, owner, patient, stranger):
    url = f"/api/v1/patients/{patient['id']}/transmissions"

    assert write(client, stranger, patient).status_code == 404
    assert client.get(url, headers=stranger).status_code == 404
    unrelated = sign_up(client, "libre@infirmo.example", ORDERS[3])
    assert client.get(url, headers=unrelated).status_code == 404
    assert (
        client.get(
            f"/api/v1/patients/{uuid.uuid4()}/transmissions", headers=owner
        ).status_code
        == 404
    )


def test_a_retained_substitute_shares_transmissions_during_the_mission(
    client, owner, office, patient, db
):
    alice, _ = hire(client, owner, office, db)

    sent = write(client, alice, patient, "Passage ce matin, tout va bien.")
    seen = client.get(
        f"/api/v1/patients/{patient['id']}/transmissions", headers=owner
    ).json()

    assert sent.status_code == 201
    assert seen["items"][0]["text"].startswith("Passage ce matin")


def test_an_unselected_candidate_gets_no_access(client, owner, office, patient, db):
    hire(client, owner, office, db)
    rejected = sign_up(client, "bob@infirmo.example", ORDERS[3])
    other_offer = client.post(
        f"/api/v1/offices/{office['id']}/offers",
        json=offer_payload(days_ahead=20),
        headers=owner,
    ).json()
    client.post(
        f"/api/v1/offers/{other_offer['id']}/applications", json={}, headers=rejected
    )

    assert write(client, rejected, patient).status_code == 404


def test_substitute_access_ends_thirty_days_after_the_mission(
    client, owner, office, patient, db
):
    alice, offer = hire(client, owner, office, db)
    now = datetime.now(UTC)
    db.execute(
        update(Offer).values(
            valid_till=now - timedelta(days=45),
            start_at=now - timedelta(days=40),
            end_at=now - timedelta(days=31),
            status="completed",
        )
    )
    db.commit()

    assert write(client, alice, patient).status_code == 404


def test_expired_transmissions_are_hidden(client, owner, patient, db):
    write(client, owner, patient, "ancienne")
    db.execute(
        update(Transmission).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    db.commit()
    write(client, owner, patient, "récente")

    items = client.get(
        f"/api/v1/patients/{patient['id']}/transmissions", headers=owner
    ).json()["items"]

    assert [t["text"] for t in items] == ["récente"]


def test_forgetting_a_patient_erases_identity_and_transmissions(
    client, owner, office, patient, db
):
    write(client, owner, patient)

    deleted = client.delete(f"/api/v1/patients/{patient['id']}", headers=owner)

    assert deleted.status_code == 204
    row = db.execute(
        text("SELECT first_name, last_name, birth_date, anonymized_at FROM patients")
    ).one()
    assert row[:3] == (None, None, None) and row[3] is not None
    assert db.scalars(select(Transmission)).all() == []
    assert (
        client.get(f"/api/v1/offices/{office['id']}/patients", headers=owner).json()[
            "total"
        ]
        == 0
    )
    assert write(client, owner, patient).status_code == 404


def test_substitutes_cannot_erase_patients(client, owner, office, patient, db):
    alice, _ = hire(client, owner, office, db)

    assert (
        client.delete(f"/api/v1/patients/{patient['id']}", headers=alice).status_code
        == 403
    )


def test_without_an_encryption_key_no_patient_is_stored(
    client, owner, office, monkeypatch, db
):
    monkeypatch.delenv("INFIRMO_ENCRYPTION_KEYS")

    response = client.post(
        f"/api/v1/offices/{office['id']}/patients", json=PATIENT, headers=owner
    )

    assert (
        response.status_code == 503
        and response.json()["code"] == "encryption_unavailable"
    )
