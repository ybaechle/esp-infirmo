import json
import os

import pytest
from sqlalchemy import update
from starlette.websockets import WebSocketDisconnect

from app import realtime
from app.api.v1 import ws
from app.models import AuthSession
from tests.helpers import ORDERS, make_office, sign_up, user_id

pytestmark = [
    pytest.mark.realtime,
    pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="REDIS_URL not set"),
]


def token_of(headers):
    return headers["Authorization"].removeprefix("Bearer ")


def connect(client, headers):
    socket = client.websocket_connect("/api/v1/ws")
    socket.__enter__()
    socket.send_json({"type": "auth", "token": token_of(headers)})
    return socket


@pytest.fixture
def pair(client, encryption_keys):
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")
    return owner, sign_up(client, "alice@infirmo.example", ORDERS[1])


def test_authenticated_socket_receives_events_addressed_to_its_user(client, pair):
    owner, alice = pair
    socket = connect(client, alice)
    try:
        assert socket.receive_json() == {"type": "ready"}
        realtime.publish([user_id_of(client, alice)], {"type": "ping.test", "n": 1})
        assert socket.receive_json() == {"type": "ping.test", "n": 1}
    finally:
        socket.__exit__(None, None, None)


def user_id_of(client, headers):
    import uuid

    return uuid.UUID(user_id(client, headers))


def test_a_message_reaches_the_recipient_live_but_not_third_parties(client, pair):
    owner, alice = pair
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers",
        json=__import__("tests.helpers", fromlist=["offer_payload"]).offer_payload(),
        headers=owner,
    ).json()
    client.post(f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice)
    conversation = client.post(
        "/api/v1/conversations", json={"user_id": user_id(client, owner)}, headers=alice
    ).json()
    outsider = sign_up(client, "autre@infirmo.example", ORDERS[2])
    listening = connect(client, owner)
    third = connect(client, outsider)
    try:
        assert listening.receive_json()["type"] == "ready"
        assert third.receive_json()["type"] == "ready"
        client.post(
            f"/api/v1/conversations/{conversation['id']}/messages",
            json={"text": "secret médical"},
            headers=alice,
        )
        event = listening.receive_json()
        assert (
            event["type"] == "message.new"
            and event["conversation_id"] == conversation["id"]
        )
        assert "secret" not in json.dumps(event)
        realtime.publish([user_id_of(client, outsider)], {"type": "only.third"})
        assert third.receive_json() == {"type": "only.third"}
    finally:
        listening.__exit__(None, None, None)
        third.__exit__(None, None, None)


@pytest.mark.parametrize(
    "first",
    [
        {"type": "auth", "token": "inconnu"},
        {"type": "hello"},
        {"type": "auth", "token": 42},
    ],
)
def test_invalid_authentication_closes_the_socket(client, first):
    with client.websocket_connect("/api/v1/ws") as socket:
        socket.send_json(first)
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == ws.UNAUTHORIZED


def test_non_json_first_message_is_rejected(client):
    with client.websocket_connect("/api/v1/ws") as socket:
        socket.send_text("pas du json")
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == ws.UNAUTHORIZED


def test_silence_is_cut_after_the_authentication_delay(client, monkeypatch):
    monkeypatch.setattr(ws, "AUTH_TIMEOUT", 0.2)
    with client.websocket_connect("/api/v1/ws") as socket:
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == ws.UNAUTHORIZED


def test_a_revoked_or_expired_token_cannot_open_a_socket(client, pair, db):
    _, alice = pair
    db.execute(update(AuthSession).values(access_expires_at=0))
    db.commit()
    with client.websocket_connect("/api/v1/ws") as socket:
        socket.send_json({"type": "auth", "token": token_of(alice)})
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
    assert closed.value.code == ws.UNAUTHORIZED


def test_the_socket_closes_when_the_access_token_expires(client, pair, db, monkeypatch):
    import time

    monkeypatch.setattr(ws, "POLL", 0.1)
    _, alice = pair
    db.execute(update(AuthSession).values(access_expires_at=int(time.time()) + 1))
    db.commit()
    socket = connect(client, alice)
    try:
        assert socket.receive_json()["type"] == "ready"
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == ws.UNAUTHORIZED
    finally:
        socket.__exit__(None, None, None)


def test_publish_is_best_effort_without_redis(monkeypatch, caplog):
    monkeypatch.delenv("REDIS_URL")

    realtime.publish([user_id_of_dummy()], {"type": "x"})

    assert "realtime publish failed: KeyError" in caplog.text


def user_id_of_dummy():
    import uuid

    return uuid.uuid4()
