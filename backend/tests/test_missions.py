import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.models import Offer
from app.services.missions import TRANSITIONS, next_status
from app.errors import ApiError
from tests.helpers import ORDERS, make_office, offer_payload, sign_up


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def offer(client, owner):
    office = make_office(client, owner)
    return client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()


@pytest.fixture
def alice(client):
    return sign_up(client, "alice@infirmo.example", ORDERS[1])


def accept(client, owner, alice, offer):
    application = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )
    return application


def act(client, headers, offer, action):
    return client.post(
        f"/api/v1/offers/{offer['id']}/status", json={"action": action}, headers=headers
    )


def started(db):
    now = datetime.now(UTC)
    db.execute(
        update(Offer).values(
            valid_till=now - timedelta(hours=2),
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(days=2),
        )
    )
    db.commit()


def test_transition_table_rejects_everything_not_listed():
    assert next_status("open", "cancel") == "cancelled"
    for status, action in [
        ("open", "start"),
        ("open", "complete"),
        ("filled", "complete"),
        ("completed", "cancel"),
        ("cancelled", "start"),
        ("in_progress", "cancel"),
    ]:
        with pytest.raises(ApiError) as error:
            next_status(status, action)
        assert error.value.code == "invalid_transition"
    assert len(TRANSITIONS) == 4


def test_full_lifecycle_open_filled_in_progress_completed(
    client, owner, alice, offer, db
):
    accept(client, owner, alice, offer)
    assert act(client, owner, offer, "start").json()["code"] == "too_early"
    started(db)

    assert act(client, owner, offer, "start").json()["status"] == "in_progress"
    assert act(client, owner, offer, "complete").json()["status"] == "completed"


def test_invalid_transitions_are_conflicts(client, owner, offer):
    skipped = act(client, owner, offer, "complete")

    assert skipped.status_code == 409 and skipped.json()["code"] == "invalid_transition"
    assert (
        client.post(
            f"/api/v1/offers/{offer['id']}/status",
            json={"action": "teleport"},
            headers=owner,
        ).status_code
        == 422
    )


def test_cancelling_an_open_or_filled_offer(client, owner, alice, offer):
    assert act(client, owner, offer, "cancel").json()["status"] == "cancelled"
    assert act(client, owner, offer, "cancel").status_code == 409


def test_status_changes_belong_to_the_offices_titulaires(client, owner, alice, offer):
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[2], "titulaire")

    assert act(client, alice, offer, "cancel").status_code == 403
    assert act(client, stranger, offer, "cancel").status_code == 404


def test_accepted_substitute_can_resign_and_the_offer_reopens(
    client, owner, alice, offer
):
    application = accept(client, owner, alice, offer)

    resigned = client.post(
        f"/api/v1/applications/{application['id']}/resign", headers=alice
    )

    assert resigned.status_code == 200 and resigned.json()["status"] == "open"
    mine = client.get("/api/v1/me/applications", headers=alice).json()["items"][0]
    assert mine["status"] == "withdrawn"
    assert client.get("/api/v1/me/missions", headers=alice).json()["total"] == 0


def test_resignation_is_refused_when_not_accepted_or_already_started(
    client, owner, alice, offer, db
):
    pending = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    refused = client.post(f"/api/v1/applications/{pending['id']}/resign", headers=alice)
    other = sign_up(client, "autre@infirmo.example", ORDERS[2])

    assert refused.status_code == 409 and refused.json()["code"] == "cannot_resign"
    assert (
        client.post(
            f"/api/v1/applications/{uuid.uuid4()}/resign", headers=alice
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/applications/{pending['id']}/resign", headers=other
        ).status_code
        == 404
    )


def test_a_started_mission_cannot_be_resigned(client, owner, alice, offer, db):
    application = accept(client, owner, alice, offer)
    started(db)
    act(client, owner, offer, "start")

    response = client.post(
        f"/api/v1/applications/{application['id']}/resign", headers=alice
    )

    assert response.status_code == 409


def test_my_missions_lists_accepted_missions_for_the_calendar(
    client, owner, alice, offer
):
    accept(client, owner, alice, offer)
    window = {
        "start_after": (datetime.now(UTC)).isoformat(),
        "end_before": (datetime.now(UTC) + timedelta(days=60)).isoformat(),
    }
    outside = {"end_before": (datetime.now(UTC) + timedelta(days=1)).isoformat()}

    inside = client.get("/api/v1/me/missions", params=window, headers=alice).json()
    nothing = client.get("/api/v1/me/missions", params=outside, headers=alice).json()

    assert inside["total"] == 1 and inside["items"][0]["offer"]["status"] == "filled"
    assert inside["items"][0]["application"]["status"] == "accepted"
    assert nothing["total"] == 0
    assert client.get("/api/v1/me/missions", headers=owner).status_code == 403


def test_open_offers_past_their_deadline_are_flagged_expired(client, owner, offer, db):
    assert (
        client.get(f"/api/v1/offers/{offer['id']}", headers=owner).json()["expired"]
        is False
    )
    db.execute(update(Offer).values(valid_till=datetime.now(UTC) - timedelta(hours=1)))
    db.commit()

    body = client.get(f"/api/v1/offers/{offer['id']}", headers=owner).json()

    assert body["expired"] is True and body["status"] == "open"
