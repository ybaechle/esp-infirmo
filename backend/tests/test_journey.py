"""Parcours complet titulaire + remplaçant sur PostgreSQL/PostGIS, du premier appel à l'oubli."""

import json
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.models import AuthSession, Offer, User
from tests.helpers import (
    ORDERS,
    make_office,
    offer_payload,
    seed_cares,
    sign_up,
    user_id,
)
from tests.test_register import PASSWORD

NANCY = (48.6921, 6.1844)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PATIENT = {
    "first_name": "Jeanne",
    "last_name": "Dupont",
    "birth_date": "1948-03-12",
    "consent": True,
}


@pytest.fixture(autouse=True)
def runtime(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))


def test_full_replacement_journey(pg_client, pg_db):
    client = pg_client
    seed_cares(pg_db, "injections", "pansements")

    # Deux professionnels, un cabinet, un administrateur pour relire la trace.
    holder = sign_up(client, "titulaire@infirmo.example", ORDERS[0], "titulaire")
    substitute = sign_up(client, "alice@infirmo.example", ORDERS[1])
    admin = sign_up(client, "admin@infirmo.example", ORDERS[2], "titulaire")
    pg_db.execute(
        update(User).where(User.email == "admin@infirmo.example").values(is_admin=True)
    )
    pg_db.commit()
    office = make_office(client, holder, latitude=NANCY[0], longitude=NANCY[1])

    # Profil, zone et disponibilités du remplaçant.
    assert (
        client.put(
            "/api/v1/profile",
            json={
                "first_name": "Alice",
                "last_name": "Martin",
                "city": "Nancy",
                "latitude": NANCY[0] + 0.01,
                "longitude": NANCY[1],
                "radius_km": 40,
                "care_codes": ["injections"],
            },
            headers=substitute,
        ).status_code
        == 200
    )
    offer_body = offer_payload(care_codes=["injections"], turnover=900)
    client.post(
        "/api/v1/availabilities",
        json={"start_at": offer_body["start_at"], "end_at": offer_body["end_at"]},
        headers=substitute,
    )

    # Publication : le remplaçant est alerté, la retrouve par recherche, avec un score élevé.
    offer = client.post(
        f"/api/v1/offices/{office['id']}/offers", json=offer_body, headers=holder
    ).json()
    alert = client.get("/api/v1/notifications", headers=substitute).json()["items"][0]
    assert alert["type"] == "offer.match" and alert["data"]["offer_id"] == offer["id"]
    found = client.get("/api/v1/offers/search", headers=substitute).json()
    assert found["total"] == 1
    top = found["items"][0]
    assert (
        top["id"] == offer["id"] and top["score"] >= 80 and top["availability"] == 1.0
    )
    assert top["distance_km"] < 5 and top["matched_cares"] == ["injections"]

    # Candidature, décision, alertes dans les deux sens.
    application = client.post(
        f"/api/v1/offers/{offer['id']}/applications",
        json={"message": "Disponible."},
        headers=substitute,
    ).json()
    assert client.get("/api/v1/offers/search", headers=substitute).json()["total"] == 0
    assert client.get("/api/v1/notifications", headers=holder).json()["items"][0][
        "type"
    ] == ("application.received")
    accepted = client.patch(
        f"/api/v1/offers/{offer['id']}/applications/{application['id']}",
        json={"decision": "accepted"},
        headers=holder,
    )
    assert accepted.json()["status"] == "accepted"
    decided = client.get("/api/v1/notifications", headers=substitute).json()["items"][0]
    assert (
        decided["type"] == "application.decided"
        and decided["data"]["decision"] == "accepted"
    )

    # Messagerie : texte, photo, lecture.
    thread = client.post(
        "/api/v1/conversations",
        json={"user_id": user_id(client, holder)},
        headers=substitute,
    ).json()
    client.post(
        f"/api/v1/conversations/{thread['id']}/messages",
        json={"text": "À demain !"},
        headers=substitute,
    )
    photo = client.post(
        f"/api/v1/conversations/{thread['id']}/photos",
        files={"file": ("p.png", PNG, "image/png")},
        headers=substitute,
    ).json()
    assert (
        client.get("/api/v1/conversations", headers=holder).json()["items"][0]["unread"]
        == 2
    )
    assert (
        client.get(f"/api/v1/messages/{photo['id']}/photo", headers=holder).content
        == PNG
    )
    client.post(f"/api/v1/conversations/{thread['id']}/read", headers=holder)
    assert (
        client.get("/api/v1/conversations", headers=holder).json()["items"][0]["unread"]
        == 0
    )

    # Transmissions partagées avec le remplaçant retenu, chiffrées au repos.
    patient = client.post(
        f"/api/v1/offices/{office['id']}/patients", json=PATIENT, headers=holder
    ).json()
    client.post(
        f"/api/v1/patients/{patient['id']}/transmissions",
        json={"text": "Insuline 12 UI"},
        headers=holder,
    )
    assert (
        client.post(
            f"/api/v1/patients/{patient['id']}/transmissions",
            json={"text": "Passage effectué."},
            headers=substitute,
        ).status_code
        == 201
    )
    shared = client.get(
        f"/api/v1/patients/{patient['id']}/transmissions", headers=substitute
    ).json()
    assert [t["text"] for t in shared["items"]] == [
        "Passage effectué.",
        "Insuline 12 UI",
    ]

    # Mission : calendrier, démarrage, fin.
    missions = client.get("/api/v1/me/missions", headers=substitute).json()
    assert (
        missions["total"] == 1 and missions["items"][0]["offer"]["status"] == "filled"
    )
    pg_db.execute(
        update(Offer).values(
            valid_till=Offer.valid_till - timedelta(days=30),
            start_at=Offer.start_at - timedelta(days=30),
        )
    )
    pg_db.commit()
    for action, expected in (("start", "in_progress"), ("complete", "completed")):
        step = client.post(
            f"/api/v1/offers/{offer['id']}/status",
            json={"action": action},
            headers=holder,
        )
        assert step.json()["status"] == expected

    # Session : le jeton d'accès expire, le refresh en émet un nouveau.
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@infirmo.example", "password": PASSWORD},
    ).json()
    pg_db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == uuid.UUID(user_id(client, substitute)))
        .values(access_expires_at=0)
    )
    pg_db.commit()
    bearer = {"Authorization": "Bearer " + tokens["access_token"]}
    assert client.get("/api/v1/auth/me", headers=bearer).status_code == 401
    renewed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).json()
    substitute = {"Authorization": "Bearer " + renewed["access_token"]}
    assert client.get("/api/v1/auth/me", headers=substitute).status_code == 200

    # Portabilité puis droit à l'oubli : le titulaire garde ses données, la trace reste lisible.
    exported = json.loads(client.get("/api/v1/me/export", headers=substitute).content)
    assert exported["profile"]["city"] == "Nancy"
    assert exported["messages_sent"][0]["text"] == "À demain !"
    assert (
        client.request(
            "DELETE", "/api/v1/me", json={"password": PASSWORD}, headers=substitute
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=holder).status_code == 200
    assert client.get("/api/v1/conversations", headers=holder).json()["total"] == 0
    trail = client.get(
        "/api/v1/admin/audit-logs", params={"limit": 100}, headers=admin
    ).json()
    names = {entry["action"] for entry in trail["items"]}
    assert {
        "auth.login",
        "patient.create",
        "transmission.create",
        "account.export",
        "account.delete",
    } <= names
    assert "Dupont" not in str(trail) and "Insuline" not in str(trail)
