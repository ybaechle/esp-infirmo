import logging
import uuid

import pytest
from sqlalchemy import select, update

from app.geo import haversine_km
from app.models import Care, DeviceToken, Notification, User
from app.services import notifications
from tests.helpers import ORDERS, make_office, offer_payload, sign_up, user_id

NANCY = (48.6921, 6.1844)
STRASBOURG = (48.5734, 7.7521)


@pytest.fixture(autouse=True)
def cares(db):
    db.add_all(
        [
            Care(code="injections", label="Injections"),
            Care(code="pansements", label="Pansements"),
        ]
    )
    db.commit()


def profile(client, headers, location=NANCY, **extra):
    body = {"first_name": "Camille", "last_name": "Démo", "radius_km": 60, **extra}
    if location:
        body.update(latitude=location[0], longitude=location[1])
    assert client.put("/api/v1/profile", json=body, headers=headers).status_code == 200


def inbox(client, headers, **params):
    return client.get("/api/v1/notifications", params=params, headers=headers).json()


def types(client, headers):
    return [n["type"] for n in inbox(client, headers)["items"]]


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def office(client, owner):
    return make_office(client, owner)


def publish(client, owner, office, **overrides):
    response = client.post(
        f"/api/v1/offices/{office['id']}/offers",
        json=offer_payload(**overrides),
        headers=owner,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_haversine_matches_the_known_nancy_strasbourg_distance():
    assert 114 < haversine_km(*NANCY, *STRASBOURG) < 118
    assert haversine_km(*NANCY, *NANCY) == 0


def test_new_offers_alert_only_substitutes_who_match_the_profile(client, owner, office):
    near = sign_up(client, "proche@infirmo.example", ORDERS[1])
    far = sign_up(client, "loin@infirmo.example", ORDERS[2])
    picky = sign_up(client, "exigeant@infirmo.example", ORDERS[3])
    wrong_cares = sign_up(client, "soins@infirmo.example", ORDERS[4])
    nowhere = sign_up(client, "inconnu@infirmo.example", "40000000006")
    profile(client, near)
    profile(client, far, location=STRASBOURG)
    profile(client, picky, min_turnover=5000)
    profile(client, wrong_cares, care_codes=["pansements"])
    profile(client, nowhere, location=None)

    offer = publish(client, owner, office, care_codes=["injections"], turnover=600)

    assert types(client, near) == ["offer.match"]
    assert inbox(client, near)["items"][0]["data"] == {"offer_id": offer["id"]}
    for silent in (far, picky, wrong_cares, nowhere, owner):
        assert inbox(client, silent)["total"] == 0


def test_office_members_and_inactive_users_are_not_alerted(client, owner, office, db):
    member = sign_up(client, "membre@infirmo.example", ORDERS[1])
    suspended = sign_up(client, "suspendu@infirmo.example", ORDERS[2])
    for headers in (member, suspended):
        profile(client, headers)
    client.post(
        f"/api/v1/offices/{office['id']}/members",
        json={"user_id": user_id(client, member)},
        headers=owner,
    )
    db.execute(
        update(User)
        .where(User.email == "suspendu@infirmo.example")
        .values(status="suspended")
    )
    db.commit()

    publish(client, owner, office)

    assert db.scalars(select(Notification)).all() == []


def apply_and_get_ids(client, owner, office):
    offer = publish(client, owner, office)
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    bob = sign_up(client, "bob@infirmo.example", ORDERS[2])
    first = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    second = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=bob
    ).json()
    return offer, alice, bob, first, second


def test_applications_alert_the_office_and_decisions_alert_every_candidate(
    client, owner, office
):
    offer, alice, bob, first, _ = apply_and_get_ids(client, owner, office)

    assert types(client, owner) == ["application.received"] * 2
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{first['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )

    assert inbox(client, alice)["items"][0]["data"]["decision"] == "accepted"
    assert inbox(client, bob)["items"][0]["data"]["decision"] == "rejected"


def test_mission_changes_alert_the_hired_substitute_and_resignations_the_office(
    client, owner, office
):
    offer, alice, _, first, _ = apply_and_get_ids(client, owner, office)
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{first['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )
    client.post(
        f"/api/v1/offers/{offer['id']}/status", json={"action": "cancel"}, headers=owner
    )

    latest = inbox(client, alice)["items"][0]
    assert (
        latest["type"] == "mission.status" and latest["data"]["status"] == "cancelled"
    )


def test_resignation_alerts_the_office(client, owner, office):
    offer, alice, _, first, _ = apply_and_get_ids(client, owner, office)
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{first['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )
    client.post(f"/api/v1/applications/{first['id']}/resign", headers=alice)

    assert inbox(client, owner)["items"][0]["data"]["status"] == "open"


def test_inbox_is_private_filterable_and_markable(client, owner, office):
    apply_and_get_ids(client, owner, office)
    first = inbox(client, owner)["items"][0]
    stranger = sign_up(client, "autre@infirmo.example", ORDERS[3], "titulaire")

    assert client.get("/api/v1/notifications/unread-count", headers=owner).json() == {
        "unread": 2
    }
    assert (
        client.post(
            f"/api/v1/notifications/{first['id']}/read", headers=stranger
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/notifications/{first['id']}/read", headers=owner
        ).status_code
        == 204
    )
    assert inbox(client, owner, unread_only=True)["total"] == 1
    assert client.post("/api/v1/notifications/read", headers=owner).status_code == 204
    assert client.get("/api/v1/notifications/unread-count", headers=owner).json() == {
        "unread": 0
    }
    assert inbox(client, stranger)["total"] == 0
    assert client.get("/api/v1/notifications").status_code == 401
    assert (
        client.post(
            f"/api/v1/notifications/{uuid.uuid4()}/read", headers=owner
        ).status_code
        == 404
    )


def test_devices_register_move_between_accounts_and_unregister(client, db):
    alice = sign_up(client, "alice@infirmo.example", ORDERS[0])
    bob = sign_up(client, "bob@infirmo.example", ORDERS[1])
    body = {"platform": "android", "token": "device-token-0001"}

    assert client.put("/api/v1/devices", json=body, headers=alice).status_code == 204
    assert client.put("/api/v1/devices", json=body, headers=bob).status_code == 204
    assert [d.user_id for d in db.scalars(select(DeviceToken))] == [
        uuid.UUID(user_id(client, bob))
    ]
    assert (
        client.delete("/api/v1/devices/device-token-0001", headers=alice).status_code
        == 404
    )
    assert (
        client.delete("/api/v1/devices/device-token-0001", headers=bob).status_code
        == 204
    )
    for invalid in (
        {"platform": "palm", "token": "device-token-0001"},
        {"platform": "ios", "token": "court"},
    ):
        assert (
            client.put("/api/v1/devices", json=invalid, headers=alice).status_code
            == 422
        )


class FakePush:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, platform, token, title, body):
        if self.fail:
            raise RuntimeError(f"provider rejected {token}")
        self.sent.append((platform, token, title, body))


def test_push_carries_generic_text_only(client, owner, office, monkeypatch):
    sender = FakePush()
    monkeypatch.setattr("app.services.push.get_push_sender", lambda: sender)
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    client.put(
        "/api/v1/devices",
        json={"platform": "ios", "token": "device-token-0002"},
        headers=alice,
    )
    profile(client, alice)

    offer = publish(client, owner, office)

    assert sender.sent == [
        (
            "ios",
            "device-token-0002",
            "Nouvelle offre",
            "Une offre correspond à votre profil.",
        )
    ]
    assert offer["id"] not in str(sender.sent)


def test_a_failing_push_provider_never_breaks_the_action_nor_leaks_the_token(
    client, owner, office, monkeypatch, caplog
):
    monkeypatch.setattr(
        "app.services.push.get_push_sender", lambda: FakePush(fail=True)
    )
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    client.put(
        "/api/v1/devices",
        json={"platform": "ios", "token": "device-token-0003"},
        headers=alice,
    )
    profile(client, alice)

    with caplog.at_level(logging.WARNING):
        response = client.post(
            f"/api/v1/offices/{office['id']}/offers",
            json=offer_payload(),
            headers=owner,
        )

    assert response.status_code == 201 and types(client, alice) == ["offer.match"]
    assert "push delivery failed: RuntimeError" in caplog.text
    assert "device-token-0003" not in caplog.text


def test_notifications_are_published_in_real_time(client, owner, office, published):
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    profile(client, alice)

    publish(client, owner, office)

    recipients, event = published[-1]
    assert recipients == {uuid.UUID(user_id(client, alice))}
    assert (
        event["type"] == "notification.new"
        and event["notification_type"] == "offer.match"
    )


def test_notify_without_recipients_does_nothing(db, published):
    notifications.notify(db, [], "offer.match", offer_id=uuid.uuid4())

    assert db.scalars(select(Notification)).all() == [] and published == []
