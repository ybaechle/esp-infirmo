import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.main import app
from app.services.ia import HttpIaClient, IaUnavailable, get_ia_client
from tests.helpers import ORDERS, make_office, offer_payload, sign_up, user_id

OGG = b"OggS\x00\x02" + b"\x00" * 40
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 40
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 16
M4A = b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 16
MP3 = b"ID3\x03\x00" + b"\x00" * 40


class FakeIa:
    def __init__(self, text="Mme Dupont, pansement refait."):
        self.text, self.calls = text, []

    def transcribe(self, audio, content_type):
        self.calls.append((audio, content_type))
        if self.text is None:
            raise IaUnavailable
        return self.text


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def ia():
    fake = FakeIa()
    app.dependency_overrides[get_ia_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_ia_client, None)


@pytest.fixture
def conversation(client):
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    alice = sign_up(client, "alice@infirmo.example", ORDERS[1])
    client.post(f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice)
    created = client.post(
        "/api/v1/conversations", json={"user_id": user_id(client, owner)}, headers=alice
    ).json()
    return alice, owner, created


def voice(client, headers, conversation, content=OGG, name="note.ogg"):
    return client.post(
        f"/api/v1/conversations/{conversation['id']}/voice",
        files={"file": (name, content, "audio/ogg")},
        headers=headers,
    )


@pytest.mark.parametrize(
    ("content", "media"),
    [
        (OGG, "audio/ogg"),
        (WEBM, "audio/webm"),
        (WAV, "audio/wav"),
        (M4A, "audio/mp4"),
        (MP3, "audio/mpeg"),
    ],
)
def test_each_supported_format_is_detected_by_content_and_transcribed(
    client, conversation, ia, content, media
):
    alice, _, thread = conversation

    sent = voice(client, alice, thread, content)

    assert sent.status_code == 201
    body = sent.json()
    assert body["has_audio"] is True and body["has_photo"] is False
    assert (
        body["transcript"].startswith("Mme Dupont")
        and body["transcript_status"] == "ready"
    )
    assert ia.calls[-1] == (content, media)


def test_non_audio_and_oversized_voice_messages_are_refused(
    client, conversation, ia, runtime
):
    alice, _, thread = conversation

    fake = voice(client, alice, thread, b"MZ\x90\x00 executable")
    huge = voice(client, alice, thread, OGG + b"0" * (10 * 1024 * 1024))

    assert fake.status_code == 422 and fake.json()["code"] == "not_audio"
    assert huge.status_code == 413
    assert list(runtime.iterdir()) == [] and ia.calls == []


def test_audio_and_transcript_are_encrypted_at_rest(
    client, conversation, ia, db, runtime
):
    from sqlalchemy import text

    alice, _, thread = conversation
    voice(client, alice, thread)

    stored = db.execute(text("SELECT transcript FROM messages")).scalar()

    assert "Dupont" not in stored
    assert b"OggS" not in next(runtime.iterdir()).read_bytes()


def test_participants_download_audio_but_outsiders_cannot(client, conversation, ia):
    alice, owner, thread = conversation
    message = voice(client, alice, thread).json()
    outsider = sign_up(client, "autre@infirmo.example", ORDERS[2])
    url = f"/api/v1/messages/{message['id']}/audio"

    served = client.get(url, headers=owner)

    assert served.content == OGG and served.headers["content-type"] == "audio/ogg"
    assert client.get(url, headers=outsider).status_code == 404
    assert (
        client.get(f"/api/v1/messages/{message['id']}/photo", headers=owner).status_code
        == 404
    )


def test_without_ia_the_voice_message_is_kept_and_the_transcript_marked_unavailable(
    client, conversation, monkeypatch
):
    monkeypatch.delenv("INFIRMO_IA_URL", raising=False)
    alice, _, thread = conversation

    sent = voice(client, alice, thread).json()

    assert sent["has_audio"] is True
    assert sent["transcript"] is None and sent["transcript_status"] == "unavailable"


def test_a_failed_transcription_can_be_retried(client, conversation, ia):
    alice, _, thread = conversation
    ia.text = None
    message = voice(client, alice, thread).json()
    assert message["transcript_status"] == "unavailable"
    ia.text = "Deuxième essai"

    retried = client.post(
        f"/api/v1/messages/{message['id']}/transcript/retry", headers=alice
    )

    assert retried.json()["transcript"] == "Deuxième essai"
    assert retried.json()["transcript_status"] == "ready"


def test_the_author_validates_and_may_correct_the_transcript(client, conversation, ia):
    alice, owner, thread = conversation
    message = voice(client, alice, thread).json()
    url = f"/api/v1/messages/{message['id']}/transcript"

    by_peer = client.post(f"{url}/validate", json={}, headers=owner)
    done = client.post(
        f"{url}/validate", json={"text": "Mme Dupont, pansement OK."}, headers=alice
    )
    again = client.post(f"{url}/validate", json={}, headers=alice)
    retry = client.post(f"{url}/retry", headers=alice)

    assert by_peer.status_code == 404
    assert done.json()["transcript"] == "Mme Dupont, pansement OK."
    assert done.json()["transcript_status"] == "validated"
    assert again.status_code == 409 and again.json()["code"] == "nothing_to_validate"
    assert retry.status_code == 409 and retry.json()["code"] == "already_validated"


def test_unavailable_transcripts_cannot_be_validated_and_text_messages_have_none(
    client, conversation, ia
):
    alice, _, thread = conversation
    ia.text = None
    message = voice(client, alice, thread).json()
    text_message = client.post(
        f"/api/v1/conversations/{thread['id']}/messages",
        json={"text": "salut"},
        headers=alice,
    ).json()

    refused = client.post(
        f"/api/v1/messages/{message['id']}/transcript/validate", json={}, headers=alice
    )

    assert refused.status_code == 409
    assert (
        text_message["has_audio"] is False and text_message["transcript_status"] is None
    )
    assert (
        client.post(
            f"/api/v1/messages/{text_message['id']}/transcript/retry", headers=alice
        ).status_code
        == 404
    )


class StubHandler(BaseHTTPRequestHandler):
    mode = "ok"
    seen = {}

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        StubHandler.seen = {
            "path": self.path,
            "type": self.headers.get("Content-Type"),
            "body": self.rfile.read(length),
        }
        mode = StubHandler.mode
        if mode == "error":
            self.send_response(500)
            self.end_headers()
            return
        payload = {
            "ok": b'{"text": "  bonjour  "}',
            "html": b"<html>nope</html>",
            "missing": b'{"transcript": "x"}',
            "number": b'{"text": 42}',
            "huge": json.dumps({"text": "x" * 30_000}).encode(),
            "big": b'{"text": "' + b"x" * 300_000 + b'"}',
        }[mode]
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub_server():
    server = HTTPServer(("127.0.0.1", 0), StubHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_http_client_follows_the_documented_contract(stub_server):
    StubHandler.mode = "ok"

    text = HttpIaClient(stub_server).transcribe(b"audio-bytes", "audio/ogg")

    assert text == "bonjour"
    assert StubHandler.seen == {
        "path": "/transcribe",
        "type": "audio/ogg",
        "body": b"audio-bytes",
    }


@pytest.mark.parametrize("mode", ["error", "html", "missing", "number", "huge", "big"])
def test_http_client_turns_every_failure_into_unavailable(stub_server, mode):
    StubHandler.mode = mode

    with pytest.raises(IaUnavailable):
        HttpIaClient(stub_server).transcribe(b"a", "audio/ogg")


def test_http_client_reports_an_unreachable_service():
    with pytest.raises(IaUnavailable):
        HttpIaClient("http://127.0.0.1:9", timeout=0.5).transcribe(b"a", "audio/ogg")


def test_client_is_built_only_when_configured(monkeypatch):
    monkeypatch.delenv("INFIRMO_IA_URL", raising=False)
    assert get_ia_client() is None
    monkeypatch.setenv("INFIRMO_IA_URL", "http://ia:8000/")
    assert get_ia_client().url == "http://ia:8000/transcribe"
