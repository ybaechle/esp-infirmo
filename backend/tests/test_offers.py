import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.models import Care, Offer
from tests.helpers import ORDERS, make_office, offer_payload, sign_up


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def office(client, owner):
    return make_office(client, owner)


@pytest.fixture
def substitute(client):
    return sign_up(client, "remplacant@infirmo.example", ORDERS[1])


@pytest.fixture(autouse=True)
def cares(db):
    db.add_all(
        [
            Care(code="injections", label="Injections"),
            Care(code="pansements", label="Pansements"),
        ]
    )
    db.commit()


def publish(client, headers, office, **overrides):
    return client.post(
        f"/api/v1/offices/{office['id']}/offers",
        json=offer_payload(**overrides),
        headers=headers,
    )


def test_titulaire_publishes_an_offer_for_their_office(client, owner, office):
    response = publish(client, owner, office, care_codes=["injections"])

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open" and body["turnover"] == 600
    assert [c["code"] for c in body["cares"]] == ["injections"]


def test_only_titulaires_who_belong_to_the_office_can_publish(
    client, owner, office, substitute
):
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    assert publish(client, substitute, office).status_code == 403
    outsider = publish(client, stranger, office)
    assert outsider.status_code == 404 and outsider.json()["code"] == "office_not_found"
    assert (
        client.post(
            f"/api/v1/offices/{office['id']}/offers", json=offer_payload()
        ).status_code
        == 401
    )


def future(days):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_at": future(5), "start_at": future(10)},
        {"valid_till": future(11)},
        {"valid_till": (datetime.now(UTC) - timedelta(days=1)).isoformat()},
        {"start_at": "2030-01-01T10:00:00"},
        {"turnover": -1},
        {"description": ""},
        {"care_codes": ["x"] * 21},
        {"unknown": 1},
    ],
)
def test_offer_input_is_validated(client, owner, office, overrides):
    assert publish(client, owner, office, **overrides).status_code == 422


def test_unknown_care_is_refused(client, owner, office):
    response = publish(client, owner, office, care_codes=["magie"])

    assert response.status_code == 422 and response.json()["code"] == "unknown_care"


def test_office_members_list_their_offers_paginated_and_filtered(
    client, owner, office, db
):
    first = publish(client, owner, office).json()
    publish(client, owner, office, days_ahead=20)
    db.execute(
        update(Offer)
        .where(Offer.id == uuid.UUID(first["id"]))
        .values(status="cancelled")
    )
    db.commit()
    url = f"/api/v1/offices/{office['id']}/offers"

    everything = client.get(url, params={"limit": 1}, headers=owner).json()
    cancelled = client.get(url, params={"status": "cancelled"}, headers=owner).json()

    assert everything["total"] == 2 and len(everything["items"]) == 1
    assert cancelled["total"] == 1
    assert client.get(url, params={"status": "bogus"}, headers=owner).status_code == 422


def test_non_members_cannot_list_an_offices_offers(client, office, substitute):
    assert (
        client.get(
            f"/api/v1/offices/{office['id']}/offers", headers=substitute
        ).status_code
        == 404
    )


def test_substitutes_see_open_offers_but_not_closed_ones(
    client, owner, office, substitute, db
):
    offer = publish(client, owner, office).json()
    url = f"/api/v1/offers/{offer['id']}"

    assert client.get(url, headers=substitute).status_code == 200
    db.execute(update(Offer).values(status="filled"))
    db.commit()
    assert client.get(url, headers=substitute).status_code == 404
    assert client.get(url, headers=owner).status_code == 200


def test_titulaires_outside_the_office_cannot_read_the_offer(client, owner, office):
    offer = publish(client, owner, office).json()
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    assert (
        client.get(f"/api/v1/offers/{offer['id']}", headers=stranger).status_code == 404
    )


def test_offers_past_their_deadline_disappear_for_substitutes(
    client, owner, office, substitute, db
):
    offer = publish(client, owner, office).json()
    db.execute(update(Offer).values(valid_till=datetime.now(UTC) - timedelta(hours=1)))
    db.commit()

    assert (
        client.get(f"/api/v1/offers/{offer['id']}", headers=substitute).status_code
        == 404
    )


def test_an_open_offer_can_be_edited_by_its_office_only(
    client, owner, office, substitute
):
    offer = publish(client, owner, office, care_codes=["injections"]).json()
    url = f"/api/v1/offers/{offer['id']}"
    change = offer_payload(turnover=900, care_codes=["pansements"])
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    updated = client.put(url, json=change, headers=owner)

    assert updated.status_code == 200 and updated.json()["turnover"] == 900
    assert [c["code"] for c in updated.json()["cares"]] == ["pansements"]
    assert client.put(url, json=change, headers=stranger).status_code == 404
    assert client.put(url, json=change, headers=substitute).status_code == 403


def test_a_filled_offer_cannot_be_edited(client, owner, office, db):
    offer = publish(client, owner, office).json()
    db.execute(update(Offer).values(status="filled"))
    db.commit()

    response = client.put(
        f"/api/v1/offers/{offer['id']}", json=offer_payload(), headers=owner
    )

    assert (
        response.status_code == 409 and response.json()["code"] == "offer_not_editable"
    )
