import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.models import Offer
from tests.helpers import (
    seed_cares,
    ORDERS,
    make_office,
    offer_payload,
    sign_up,
    user_id,
)


@pytest.fixture(autouse=True)
def cares(db):
    seed_cares(db, "injections")


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def offer(client, owner):
    office = make_office(client, owner)
    response = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    )
    return response.json()


@pytest.fixture
def alice(client):
    return sign_up(client, "alice@infirmo.example", ORDERS[1])


@pytest.fixture
def bob(client):
    return sign_up(client, "bob@infirmo.example", ORDERS[2])


def apply(client, headers, offer, message=None):
    return client.post(
        f"/api/v1/offers/{offer['id']}/applications",
        json={"message": message} if message else {},
        headers=headers,
    )


def candidates(client, headers, offer, **params):
    return client.get(
        f"/api/v1/offers/{offer['id']}/applications", params=params, headers=headers
    ).json()


def decide(client, headers, offer, application, decision):
    return client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": decision},
        headers=headers,
    )


def test_a_substitute_applies_once_per_offer(client, offer, alice):
    first = apply(client, alice, offer, "Disponible dès le 1er.")
    second = apply(client, alice, offer)

    assert first.status_code == 201 and first.json()["status"] == "pending"
    assert second.status_code == 409 and second.json()["code"] == "already_applied"


def test_only_substitutes_apply_and_never_to_their_own_office(
    client, owner, offer, alice
):
    other_owner = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    assert apply(client, owner, offer).status_code == 403
    assert apply(client, other_owner, offer).status_code == 403
    assert (
        client.post(f"/api/v1/offers/{offer['id']}/applications", json={}).status_code
        == 401
    )
    assert apply(client, alice, {"id": str(uuid.uuid4())}).status_code == 404


def test_a_member_substitute_cannot_apply_to_their_own_offices_offer(
    client, owner, offer, alice
):
    office_id = offer["office_id"]
    client.post(
        f"/api/v1/offices/{office_id}/members",
        json={"user_id": user_id(client, alice)},
        headers=owner,
    )

    assert apply(client, alice, offer).status_code == 404


def test_closed_or_expired_offers_refuse_applications(client, offer, alice, bob, db):
    db.execute(update(Offer).values(valid_till=datetime.now(UTC) - timedelta(hours=1)))
    db.commit()
    expired = apply(client, alice, offer)
    db.execute(update(Offer).values(status="filled"))
    db.commit()
    closed = apply(client, bob, offer)

    assert expired.status_code == closed.status_code == 409
    assert closed.json()["code"] == "offer_closed"


def test_message_is_bounded(client, offer, alice):
    assert apply(client, alice, offer, "x" * 501).status_code == 422


def test_office_members_review_candidates_with_their_profile(
    client, owner, offer, alice
):
    client.put(
        "/api/v1/profile",
        json={
            "first_name": "Alice",
            "last_name": "Martin",
            "city": "Metz",
            "care_codes": ["injections"],
        },
        headers=alice,
    )
    apply(client, alice, offer, "Bonjour")

    listing = candidates(client, owner, offer)

    assert listing["total"] == 1
    candidate = listing["items"][0]
    assert candidate["first_name"] == "Alice" and candidate["city"] == "Metz"
    assert (
        candidate["cares"][0]["code"] == "injections"
        and candidate["message"] == "Bonjour"
    )
    assert "email" not in candidate and "password_hash" not in str(candidate)


def test_candidates_are_hidden_from_outsiders_and_substitutes(client, offer, alice):
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")
    url = f"/api/v1/offers/{offer['id']}/applications"

    assert client.get(url, headers=alice).status_code == 403
    assert client.get(url, headers=stranger).status_code == 404
    assert client.get(
        url, params={"status": "bogus"}, headers=stranger
    ).status_code in (404, 422)


def test_accepting_one_candidate_fills_the_offer_and_rejects_the_others(
    client, owner, offer, alice, bob
):
    first, second = apply(client, alice, offer).json(), apply(client, bob, offer).json()

    accepted = decide(client, owner, offer, first, "accepted")

    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    assert (
        client.get(f"/api/v1/offers/{offer['id']}", headers=owner).json()["status"]
        == "filled"
    )
    statuses = [c["status"] for c in candidates(client, owner, offer)["items"]]
    assert sorted(statuses) == ["accepted", "rejected"]
    late = decide(client, owner, offer, second, "accepted")
    assert late.status_code == 409 and late.json()["code"] == "already_decided"


def test_a_decision_cannot_be_replayed_or_changed(client, owner, offer, alice):
    application = apply(client, alice, offer).json()
    decide(client, owner, offer, application, "rejected")

    again = decide(client, owner, offer, application, "accepted")

    assert again.status_code == 409 and again.json()["code"] == "already_decided"


def test_decisions_are_for_titulaires_of_the_office_only(client, owner, offer, alice):
    application = apply(client, alice, offer).json()
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    assert decide(client, alice, offer, application, "accepted").status_code == 403
    assert decide(client, stranger, offer, application, "accepted").status_code == 404
    assert (
        decide(client, owner, offer, {"id": str(uuid.uuid4())}, "accepted").status_code
        == 404
    )
    bad = client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": "maybe"},
        headers=owner,
    )
    assert bad.status_code == 422


def test_a_pending_application_can_be_withdrawn_only_by_its_author(
    client, offer, alice, bob
):
    application = apply(client, alice, offer).json()
    url = f"/api/v1/applications/{application['id']}"

    assert client.delete(url, headers=bob).status_code == 404
    assert client.delete(url, headers=alice).status_code == 204
    again = client.delete(url, headers=alice)
    assert again.status_code == 409 and again.json()["code"] == "not_pending"


def test_my_applications_lists_mine_with_their_offer(client, offer, alice, bob):
    apply(client, alice, offer)

    mine = client.get("/api/v1/me/applications", headers=alice).json()

    assert mine["total"] == 1 and mine["items"][0]["offer"]["id"] == offer["id"]
    assert client.get("/api/v1/me/applications", headers=bob).json()["total"] == 0


def test_substitute_cannot_apply_twice_even_after_withdrawing(client, offer, alice):
    application = apply(client, alice, offer).json()
    client.delete(f"/api/v1/applications/{application['id']}", headers=alice)

    assert apply(client, alice, offer).status_code == 409


def test_two_simultaneous_acceptances_fill_the_offer_only_once(pg_client):
    client = pg_client
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")
    other_member = sign_up(client, "second@infirmo.example", ORDERS[1], "titulaire")
    office = make_office(client, owner)
    client.post(
        f"/api/v1/offices/{office['id']}/members",
        json={"user_id": user_id(client, other_member)},
        headers=owner,
    )
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    first = apply(client, sign_up(client, "a@infirmo.example", ORDERS[2]), offer).json()
    second = apply(
        client, sign_up(client, "b@infirmo.example", ORDERS[3]), offer
    ).json()
    barrier = threading.Barrier(2)
    codes = []

    def accept(headers, application):
        barrier.wait()
        codes.append(
            decide(client, headers, offer, application, "accepted").status_code
        )

    threads = [
        threading.Thread(target=accept, args=(owner, first)),
        threading.Thread(target=accept, args=(other_member, second)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert sorted(codes) == [200, 409]
    done = candidates(client, owner, offer)["items"]
    assert sorted(c["status"] for c in done) == ["accepted", "rejected"]


def test_acceptance_rereads_the_offer_after_taking_the_lock(pg_client, pg_engine):
    """Une autre transaction a déjà rempli l'offre alors que la session en garde une copie périmée."""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from app.database import get_db
    from app.main import app

    client = pg_client
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    pending = apply(
        client, sign_up(client, "a@infirmo.example", ORDERS[1]), offer
    ).json()

    stale = Session(pg_engine)
    stale.get(Offer, uuid.UUID(offer["id"]))
    with pg_engine.begin() as other:
        other.execute(
            text("UPDATE offers SET status = 'filled' WHERE id = :id"),
            {"id": offer["id"]},
        )
    app.dependency_overrides[get_db] = lambda: stale
    try:
        response = decide(client, owner, offer, pending, "accepted")
    finally:
        stale.close()

    assert response.status_code == 409 and response.json()["code"] == "offer_closed"
