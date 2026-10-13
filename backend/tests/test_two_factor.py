import pytest
from sqlalchemy import select, update

from app.main import app
from app.models import TwoFactorChallenge, User
from app.services.otp import OtpUnavailable, get_otp_sender

from tests.test_register import PASSWORD, payload

EMAIL = "camille.demo@infirmo.example"


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, channel, destination, code):
        self.sent.append((channel, destination, code))


@pytest.fixture
def sender():
    fake = FakeSender()
    app.dependency_overrides[get_otp_sender] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_otp_sender, None)


@pytest.fixture
def session(client):
    client.post("/api/v1/auth/register", json=payload())
    tokens = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).json()
    return {"Authorization": "Bearer " + tokens["access_token"]}


def enable_email(client, session, sender):
    challenge = client.post(
        "/api/v1/auth/2fa/enable", json={"channel": "email"}, headers=session
    ).json()["challenge_id"]
    code = sender.sent[-1][2]
    confirm = client.post(
        "/api/v1/auth/2fa/confirm",
        json={"challenge_id": challenge, "code": code},
        headers=session,
    )
    assert confirm.status_code == 204


def login(client):
    return client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )


def test_enable_sends_a_code_to_the_account_email_and_confirm_turns_it_on(
    client, session, sender, db
):
    enable_email(client, session, sender)

    assert sender.sent[0][:2] == ("email", EMAIL)
    assert db.scalar(select(User.two_factor_channel)) == "email"


def test_login_with_2fa_requires_the_code_before_issuing_tokens(
    client, session, sender
):
    enable_email(client, session, sender)

    first = login(client).json()
    assert first["two_factor_required"] is True and first["access_token"] is None
    code = sender.sent[-1][2]
    done = client.post(
        "/api/v1/auth/2fa/verify",
        json={"challenge_id": first["challenge_id"], "code": code},
    ).json()

    assert done["access_token"] and done["two_factor_required"] is False
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer " + done["access_token"]}
    )
    assert me.status_code == 200


def test_a_code_is_single_use_and_bound_to_its_challenge(client, session, sender):
    enable_email(client, session, sender)
    challenge = login(client).json()["challenge_id"]
    code = sender.sent[-1][2]
    body = {"challenge_id": challenge, "code": code}

    assert client.post("/api/v1/auth/2fa/verify", json=body).status_code == 200
    replay = client.post("/api/v1/auth/2fa/verify", json=body)

    assert replay.status_code == 401 and replay.json()["code"] == "invalid_code"


def test_wrong_codes_are_limited_to_five_attempts(client, session, sender):
    enable_email(client, session, sender)
    challenge = login(client).json()["challenge_id"]
    good = sender.sent[-1][2]
    wrong = "000000" if good != "000000" else "111111"

    for _ in range(5):
        r = client.post(
            "/api/v1/auth/2fa/verify", json={"challenge_id": challenge, "code": wrong}
        )
        assert r.status_code == 401
    late = client.post(
        "/api/v1/auth/2fa/verify", json={"challenge_id": challenge, "code": good}
    )

    assert late.status_code == 401


def test_expired_code_is_refused(client, session, sender, db):
    enable_email(client, session, sender)
    challenge = login(client).json()["challenge_id"]
    db.execute(update(TwoFactorChallenge).values(expires_at=0))
    db.commit()

    response = client.post(
        "/api/v1/auth/2fa/verify",
        json={"challenge_id": challenge, "code": sender.sent[-1][2]},
    )

    assert response.status_code == 401


def test_code_is_stored_hashed(client, session, sender, db):
    client.post("/api/v1/auth/2fa/enable", json={"channel": "email"}, headers=session)

    assert sender.sent[-1][2] not in db.scalar(select(TwoFactorChallenge.code_hash))


def test_disable_requires_the_password(client, session, sender, db):
    enable_email(client, session, sender)

    denied = client.post(
        "/api/v1/auth/2fa/disable",
        json={"password": "Mauvais-2026-xx"},
        headers=session,
    )
    ok = client.post(
        "/api/v1/auth/2fa/disable", json={"password": PASSWORD}, headers=session
    )

    assert denied.status_code == 401 and ok.status_code == 204
    assert db.scalar(select(User.two_factor_channel)) is None
    assert login(client).json()["access_token"]


def test_sms_needs_a_valid_phone_number(client, session, sender):
    no_phone = client.post(
        "/api/v1/auth/2fa/enable", json={"channel": "sms"}, headers=session
    )
    bad_phone = client.post(
        "/api/v1/auth/2fa/enable",
        json={"channel": "sms", "phone": "0612345678"},
        headers=session,
    )
    good = client.post(
        "/api/v1/auth/2fa/enable",
        json={"channel": "sms", "phone": "+33612345678"},
        headers=session,
    )

    assert no_phone.status_code == 422 and no_phone.json()["code"] == "phone_required"
    assert bad_phone.status_code == 422
    assert good.status_code == 202 and sender.sent[-1][:2] == ("sms", "+33612345678")


def test_without_a_configured_provider_enabling_fails_closed(client, session):
    response = client.post(
        "/api/v1/auth/2fa/enable", json={"channel": "email"}, headers=session
    )

    assert response.status_code == 503 and response.json()["code"] == "otp_unavailable"


def test_login_stays_closed_when_the_provider_goes_down(client, session, sender, db):
    enable_email(client, session, sender)

    class Down:
        def send(self, *args):
            raise OtpUnavailable

    app.dependency_overrides[get_otp_sender] = lambda: Down()

    assert login(client).status_code == 503


def test_two_factor_routes_require_authentication(client):
    assert (
        client.post("/api/v1/auth/2fa/enable", json={"channel": "email"}).status_code
        == 401
    )
