import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.models import (
    Application,
    AuditLog,
    AuthSession,
    Conversation,
    Document,
    Message,
    Patient,
    Transmission,
    TwoFactorChallenge,
    User,
)
from app.promote_admin import promote
from app.services.purge import purge
from tests.helpers import ORDERS, make_office, offer_payload, sign_up, user_id
from tests.test_register import PASSWORD

PDF = b"%PDF-1.7\n%%EOF\n"
EMAIL = "alice@infirmo.example"


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def owner(client):
    return sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")


@pytest.fixture
def alice(client):
    return sign_up(client, EMAIL, ORDERS[1])


def erase(client, headers, password=PASSWORD):
    return client.request(
        "DELETE", "/api/v1/me", json={"password": password}, headers=headers
    )


def test_account_deletion_requires_the_password(client, alice, db):
    assert erase(client, alice, "mauvais").status_code == 401
    assert db.scalar(select(User.status).where(User.email == EMAIL)) == "active"


def test_deletion_erases_personal_data_and_closes_the_account(
    client, owner, alice, db, runtime
):
    client.put(
        "/api/v1/profile",
        json={"first_name": "Alice", "last_name": "Martin", "city": "Metz"},
        headers=alice,
    )
    client.post(
        "/api/v1/documents",
        data={"doc_type": "rib"},
        files={"file": ("x.pdf", PDF, "application/pdf")},
        headers=alice,
    )
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    pending = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    conversation = client.post(
        "/api/v1/conversations", json={"user_id": user_id(client, owner)}, headers=alice
    ).json()
    client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"text": "Bonjour"},
        headers=alice,
    )
    identifier = user_id(client, alice)

    assert erase(client, alice).status_code == 204

    user = db.get(User, uuid.UUID(identifier))
    db.refresh(user)
    assert user.status == "deleted" and EMAIL not in user.email
    assert (user.first_name, user.phone, user.two_factor_channel) == (
        "Compte",
        None,
        None,
    )
    assert db.scalars(select(Document)).all() == [] and list(runtime.iterdir()) == []
    assert (
        db.scalars(select(Message)).all() == []
        and db.scalars(select(Conversation)).all() == []
    )
    assert (
        db.scalars(select(AuthSession).where(AuthSession.user_id == user.id)).all()
        == []
    )
    assert db.get(Application, uuid.UUID(pending["id"])).status == "withdrawn"
    assert client.get("/api/v1/auth/me", headers=alice).status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 401
    assert client.get("/api/v1/auth/me", headers=owner).status_code == 200
    assert db.scalar(select(AuditLog.action).where(AuditLog.action == "account.delete"))


def test_deleted_identity_can_register_again(client, alice):
    erase(client, alice)

    again = client.post(
        "/api/v1/auth/register",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "first_name": "Alice",
            "last_name": "Martin",
            "role": "remplacant",
            "order_number": ORDERS[1],
            "accept_terms": True,
        },
    )

    assert again.status_code == 201


def test_accounts_with_active_missions_cannot_be_deleted(client, owner, alice, db):
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()

    blocked_owner = erase(client, owner)
    application = client.post(
        f"/api/v1/offers/{offer['id']}/applications", json={}, headers=alice
    ).json()
    client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": "accepted"},
        headers=owner,
    )
    blocked_substitute = erase(client, alice)

    assert blocked_owner.status_code == blocked_substitute.status_code == 409
    assert blocked_owner.json()["code"] == "active_missions"
    client.post(
        f"/api/v1/offers/{offer['id']}/status", json={"action": "cancel"}, headers=owner
    )
    assert erase(client, alice).status_code == 204
    assert erase(client, owner).status_code == 204


def test_administrators_cannot_delete_themselves(client, alice, db):
    db.execute(update(User).values(is_admin=True))
    db.commit()

    response = erase(client, alice)

    assert (
        response.status_code == 409 and response.json()["code"] == "admin_cannot_delete"
    )


def test_export_gathers_what_the_user_provided(client, owner, alice):
    client.put(
        "/api/v1/profile",
        json={
            "first_name": "Alice",
            "last_name": "Martin",
            "city": "Metz",
            "radius_km": 25,
        },
        headers=alice,
    )
    client.post(
        "/api/v1/availabilities",
        json={
            "start_at": datetime.now(UTC).isoformat(),
            "end_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
        headers=alice,
    )
    office = make_office(client, owner)
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_payload(), headers=owner
    ).json()
    client.post(
        f"/api/v1/offers/{offer['id']}/applications",
        json={"message": "Candidate"},
        headers=alice,
    )
    conversation = client.post(
        "/api/v1/conversations", json={"user_id": user_id(client, owner)}, headers=alice
    ).json()
    client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"text": "Bonjour docteur"},
        headers=alice,
    )

    response = client.get("/api/v1/me/export", headers=alice)

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = json.loads(response.content)
    assert data["account"]["email"] == EMAIL
    assert data["profile"]["city"] == "Metz" and len(data["availabilities"]) == 1
    assert data["applications"][0]["message"] == "Candidate"
    assert data["messages_sent"][0]["text"] == "Bonjour docteur"
    assert "password" not in response.text
    assert client.get("/api/v1/me/export").status_code == 401


def test_export_is_traced(client, alice, db):
    client.get("/api/v1/me/export", headers=alice)

    assert db.scalar(select(AuditLog.action).where(AuditLog.action == "account.export"))


def test_purge_applies_retention_and_keeps_live_data(client, owner, alice, db):
    office = make_office(client, owner)
    patient = Patient(
        office_id=uuid.UUID(office["id"]),
        created_by=uuid.UUID(user_id(client, owner)),
        consent_at=datetime.now(UTC),
    )
    db.add(patient)
    db.flush()
    author = patient.created_by
    now = datetime.now(UTC)
    db.add_all(
        [
            Transmission(
                patient_id=patient.id,
                author_id=author,
                text="vieille",
                expires_at=now - timedelta(days=1),
            ),
            Transmission(
                patient_id=patient.id,
                author_id=author,
                text="valide",
                expires_at=now + timedelta(days=5),
            ),
            AuditLog(action="old", at=now - timedelta(days=400)),
            AuditLog(action="recent", at=now - timedelta(days=10)),
            TwoFactorChallenge(
                user_id=author,
                purpose="login",
                channel="email",
                code_hash="x",
                expires_at=int(time.time()) - 5,
            ),
        ]
    )
    db.execute(
        update(AuthSession)
        .values(refresh_expires_at=int(time.time()) - 5)
        .where(AuthSession.user_id == author)
    )
    db.commit()

    counts = purge(db)

    assert (
        counts["transmissions"] == 1
        and counts["challenges"] == 1
        and counts["sessions"] >= 1
    )
    assert counts["audit_logs"] == 1
    assert [t.text for t in db.scalars(select(Transmission))] == ["valide"]
    assert "recent" in {a.action for a in db.scalars(select(AuditLog))}
    assert db.scalars(select(AuthSession).where(AuthSession.user_id != author)).all()


def test_promote_admin_flags_an_active_account_only(client, alice, db):
    promote(db, "ALICE@infirmo.example")

    assert db.scalar(select(User.is_admin).where(User.email == EMAIL)) is True
    with pytest.raises(SystemExit):
        promote(db, "inconnu@infirmo.example")
    assert db.scalar(select(AuditLog.action).where(AuditLog.action == "admin.promote"))


def test_cli_entry_points_run_against_the_configured_database(
    pg_engine, monkeypatch, capsys
):
    from app import promote_admin, purge as purge_cli

    purge_cli.main()
    assert json.loads(capsys.readouterr().out).keys() == {
        "transmissions",
        "sessions",
        "challenges",
        "audit_logs",
    }
    monkeypatch.setattr("sys.argv", ["promote_admin"])
    with pytest.raises(SystemExit):
        promote_admin.main()
