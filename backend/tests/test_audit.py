from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import DBAPIError

from app.models import User
from tests.helpers import ORDERS, make_office, sign_up, user_id
from tests.test_register import PASSWORD

PDF = b"%PDF-1.7\n%%EOF\n"
PATIENT = {
    "first_name": "Jeanne",
    "last_name": "Dupont",
    "birth_date": "1948-03-12",
    "consent": True,
}


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))


@pytest.fixture
def admin(client, db):
    headers = sign_up(client, "admin@infirmo.example", ORDERS[0], "titulaire")
    db.execute(
        update(User).where(User.email == "admin@infirmo.example").values(is_admin=True)
    )
    db.commit()
    return headers


def trail(client, admin, **params):
    response = client.get("/api/v1/admin/audit-logs", params=params, headers=admin)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def actions(client, admin, **params):
    return [(e["action"], e["outcome"]) for e in trail(client, admin, **params)]


def test_logins_are_traced_with_their_outcome(client, admin):
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@infirmo.example", "password": "faux"},
    )
    client.post(
        "/api/v1/auth/login", json={"email": "inconnu@infirmo.example", "password": "x"}
    )

    seen = actions(client, admin, action="auth.login")

    assert ("auth.login", "success") in seen
    assert seen.count(("auth.login", "failure")) == 2


def test_suspended_account_login_is_traced_as_denied(client, admin, db):
    sign_up(client, "membre@infirmo.example", ORDERS[1])
    db.execute(
        update(User)
        .where(User.email == "membre@infirmo.example")
        .values(status="suspended")
    )
    db.commit()
    client.post(
        "/api/v1/auth/login",
        json={"email": "membre@infirmo.example", "password": PASSWORD},
    )

    assert ("auth.login", "denied") in actions(client, admin)


def test_sensitive_actions_leave_a_trace_without_any_content(client, admin):
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[2], "titulaire")
    office = make_office(client, owner)
    patient = client.post(
        f"/api/v1/offices/{office['id']}/patients", json=PATIENT, headers=owner
    ).json()
    client.post(
        f"/api/v1/patients/{patient['id']}/transmissions",
        json={"text": "Insuline 12 UI"},
        headers=owner,
    )
    client.get(f"/api/v1/patients/{patient['id']}/transmissions", headers=owner)
    document = client.post(
        "/api/v1/documents",
        data={"doc_type": "rib"},
        files={"file": ("x.pdf", PDF, "application/pdf")},
        headers=owner,
    ).json()
    client.get(f"/api/v1/documents/{document['id']}/file", headers=owner)
    client.delete(f"/api/v1/patients/{patient['id']}", headers=owner)

    log = trail(client, admin, limit=100)
    names = {e["action"] for e in log}

    assert {
        "patient.create",
        "transmission.create",
        "transmission.read",
        "document.upload",
        "document.download",
        "patient.forget",
    } <= names
    blob = str(log)
    assert "Dupont" not in blob and "Insuline" not in blob and "titulaire@" not in blob
    read = next(e for e in log if e["action"] == "transmission.read")
    assert read["resource_id"] == patient["id"] and read["actor_id"] == user_id(
        client, owner
    )


def test_denied_access_to_a_patient_is_traced(client, admin):
    owner = sign_up(client, "titulaire@infirmo.example", ORDERS[2], "titulaire")
    office = make_office(client, owner)
    patient = client.post(
        f"/api/v1/offices/{office['id']}/patients", json=PATIENT, headers=owner
    ).json()
    outsider = sign_up(client, "autre@infirmo.example", ORDERS[3], "titulaire")

    client.get(f"/api/v1/patients/{patient['id']}/transmissions", headers=outsider)

    denied = [e for e in trail(client, admin) if e["outcome"] == "denied"]
    assert denied and denied[0]["action"] == "patient.access"
    assert denied[0]["actor_id"] == user_id(client, outsider)


def test_admin_decisions_are_traced(client, admin):
    member = sign_up(client, "membre@infirmo.example", ORDERS[1])
    client.patch(
        f"/api/v1/admin/users/{user_id(client, member)}",
        json={"status": "suspended"},
        headers=admin,
    )

    assert ("admin.user_status", "success") in actions(client, admin)


def test_audit_log_filters_and_is_admin_only(client, admin):
    member = sign_up(client, "membre@infirmo.example", ORDERS[1])
    me = user_id(client, member)
    day_ahead = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    long_ago = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    only_member = trail(client, admin, actor_id=me)
    none_yet = trail(client, admin, since=day_ahead)
    everything = trail(client, admin, since=long_ago, until=day_ahead)

    assert only_member and all(e["actor_id"] == me for e in only_member)
    assert none_yet == [] and len(everything) >= len(only_member)
    assert client.get("/api/v1/admin/audit-logs", headers=member).status_code == 403
    assert client.get("/api/v1/admin/audit-logs").status_code == 401


def test_2fa_changes_are_traced(client, admin):
    from app.main import app
    from app.services.otp import get_otp_sender

    class Sender:
        code = None

        def send(self, channel, destination, code):
            Sender.code = code

    app.dependency_overrides[get_otp_sender] = lambda: Sender()
    member = sign_up(client, "membre@infirmo.example", ORDERS[1])
    challenge = client.post(
        "/api/v1/auth/2fa/enable", json={"channel": "email"}, headers=member
    ).json()["challenge_id"]
    client.post(
        "/api/v1/auth/2fa/confirm",
        json={"challenge_id": challenge, "code": Sender.code},
        headers=member,
    )
    client.post("/api/v1/auth/2fa/disable", json={"password": PASSWORD}, headers=member)

    names = {a for a, _ in actions(client, admin)}

    assert {"auth.2fa_enabled", "auth.2fa_disabled"} <= names


def test_audit_table_is_append_only_during_retention_on_postgresql(pg_engine, pg_db):
    from uuid import uuid4

    log_id, old_id = uuid4(), uuid4()
    pg_db.execute(
        text(
            "INSERT INTO audit_logs (id, at, action, outcome) VALUES (:i, now(), 'x', 'success')"
        ),
        {"i": log_id},
    )
    pg_db.execute(
        text(
            "INSERT INTO audit_logs (id, at, action, outcome) "
            "VALUES (:i, now() - interval '400 days', 'x', 'success')"
        ),
        {"i": old_id},
    )
    pg_db.commit()

    for statement in (
        "UPDATE audit_logs SET action = 'y' WHERE id = :i",
        "DELETE FROM audit_logs WHERE id = :i",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            pg_db.execute(text(statement), {"i": log_id})
        pg_db.rollback()

    pg_db.execute(text("DELETE FROM audit_logs WHERE id = :i"), {"i": old_id})
    pg_db.commit()
    remaining = pg_db.execute(text("SELECT count(*) FROM audit_logs")).scalar()
    assert remaining == 1
