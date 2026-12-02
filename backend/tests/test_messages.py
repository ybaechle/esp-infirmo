import uuid

import pytest
from sqlalchemy import text

from tests.helpers import ORDERS, make_office, offer_payload, sign_up, user_id

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def alice(client, owner):
    """Candidate à une offre du cabinet de `owner` : elle peut lui écrire."""
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    headers = sign_up(client, "alice@infirmo.example", ORDERS[1])
    client.post(f"/api/v1/offers/{offer['id']}/applications", json={}, headers=headers)
    return headers


@pytest.fixture
def stranger(client):
    return sign_up(client, "autre@infirmo.example", ORDERS[2])


def open_with(client, headers, target):
    return client.post(
        "/api/v1/conversations",
        json={"user_id": user_id(client, target)},
        headers=headers,
    )


def test_connected_professionals_open_one_conversation_only(client, owner, alice):
    first = open_with(client, owner, alice)
    again = open_with(client, alice, owner)

    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert first.json()["peer"]["first_name"] == "Camille"


def test_unrelated_users_cannot_start_a_conversation(client, owner, alice, stranger):
    refused = open_with(client, stranger, owner)
    self_chat = open_with(client, owner, owner)

    assert refused.status_code == 403 and refused.json()["code"] == "not_connected"
    assert self_chat.status_code == 404
    assert (
        client.post(
            "/api/v1/conversations", json={"user_id": str(uuid.uuid4())}, headers=owner
        ).status_code
        == 404
    )


def test_members_of_the_same_office_can_talk(client, owner, stranger):
    office = make_office(client, owner)
    colleague = sign_up(client, "collegue@infirmo.example", ORDERS[3], "titulaire")
    client.post(
        f"/api/v1/offices/{office['id']}/members",
        json={"user_id": user_id(client, colleague)},
        headers=owner,
    )

    assert open_with(client, colleague, owner).status_code == 201


def send(client, headers, conversation, body):
    return client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json=body,
        headers=headers,
    )


def test_text_messages_flow_both_ways_newest_first(client, owner, alice):
    conversation = open_with(client, owner, alice).json()
    send(client, owner, conversation, {"text": "Bonjour"})
    send(client, alice, conversation, {"text": "Bonjour, je suis disponible."})

    listing = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages", headers=alice
    ).json()

    assert listing["total"] == 2
    assert listing["items"][0]["text"] == "Bonjour, je suis disponible."


def test_message_body_is_encrypted_in_the_database(client, owner, alice, db):
    conversation = open_with(client, owner, alice).json()
    send(client, owner, conversation, {"text": "Mme Dupont, diabète"})

    stored = db.execute(text("SELECT body FROM messages")).scalar()

    assert "Dupont" not in stored and "diabète" not in stored


@pytest.mark.parametrize(
    "body", [{"text": ""}, {"text": "x" * 4001}, {}, {"text": "ok", "x": 1}]
)
def test_message_input_is_validated(client, owner, alice, body):
    conversation = open_with(client, owner, alice).json()

    assert send(client, owner, conversation, body).status_code == 422


def test_non_participants_see_nothing(client, owner, alice, stranger):
    conversation = open_with(client, owner, alice).json()

    assert send(client, stranger, conversation, {"text": "intrus"}).status_code == 404
    url = f"/api/v1/conversations/{conversation['id']}/messages"
    assert client.get(url, headers=stranger).status_code == 404
    assert client.get("/api/v1/conversations", headers=stranger).json()["total"] == 0


def test_unread_counter_and_mark_as_read(client, owner, alice):
    conversation = open_with(client, owner, alice).json()
    send(client, owner, conversation, {"text": "1"})
    send(client, owner, conversation, {"text": "2"})

    before = client.get("/api/v1/conversations", headers=alice).json()["items"][0]
    sender_view = client.get("/api/v1/conversations", headers=owner).json()["items"][0]
    done = client.post(
        f"/api/v1/conversations/{conversation['id']}/read", headers=alice
    )
    after = client.get("/api/v1/conversations", headers=alice).json()["items"][0]

    assert before["unread"] == 2 and sender_view["unread"] == 0
    assert done.status_code == 204 and after["unread"] == 0


def test_conversations_are_ordered_by_latest_activity(client, owner, alice):
    second = sign_up(client, "bob@infirmo.example", ORDERS[3], "titulaire")
    office = client.get("/api/v1/offices", headers=owner).json()[0]
    client.post(
        f"/api/v1/offices/{office['id']}/members",
        json={"user_id": user_id(client, second)},
        headers=owner,
    )
    older = open_with(client, owner, alice).json()
    newer = open_with(client, owner, second).json()
    send(client, owner, older, {"text": "ancien"})
    send(client, owner, newer, {"text": "récent"})
    send(client, owner, older, {"text": "dernier"})

    ids = [
        c["id"]
        for c in client.get("/api/v1/conversations", headers=owner).json()["items"]
    ]

    assert ids == [older["id"], newer["id"]]


def photo(client, headers, conversation, content, name="photo.png", text=None):
    return client.post(
        f"/api/v1/conversations/{conversation['id']}/photos",
        files={"file": (name, content, "image/png")},
        data={"text": text} if text else {},
        headers=headers,
    )


def test_photo_is_checked_by_content_encrypted_and_served_to_participants(
    client, owner, alice, stranger, storage_dir
):
    conversation = open_with(client, owner, alice).json()

    sent = photo(client, alice, conversation, PNG, "../../x.exe", text="Plaie J+2")

    assert sent.status_code == 201 and sent.json()["has_photo"] is True
    files = list(storage_dir.iterdir())
    assert len(files) == 1 and b"PNG" not in files[0].read_bytes()
    url = f"/api/v1/messages/{sent.json()['id']}/photo"
    served = client.get(url, headers=owner)
    assert served.content == PNG and served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert client.get(url, headers=stranger).status_code == 404
    assert photo(client, alice, conversation, JPEG).status_code == 201


def test_non_images_and_oversized_photos_are_refused(client, owner, alice, storage_dir):
    conversation = open_with(client, owner, alice).json()

    fake = photo(client, alice, conversation, b"<svg onload=alert(1)>")
    huge = photo(client, alice, conversation, PNG + b"0" * (5 * 1024 * 1024))

    assert fake.status_code == 422 and fake.json()["code"] == "not_an_image"
    assert huge.status_code == 413
    assert list(storage_dir.iterdir()) == []


def test_text_messages_have_no_photo_to_download(client, owner, alice):
    conversation = open_with(client, owner, alice).json()
    message = send(client, owner, conversation, {"text": "salut"}).json()

    assert (
        client.get(f"/api/v1/messages/{message['id']}/photo", headers=owner).status_code
        == 404
    )


def test_messaging_requires_authentication(client):
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.post("/api/v1/conversations", json={}).status_code == 401
