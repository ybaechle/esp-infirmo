from datetime import UTC, datetime, timedelta

import pytest

from app.services.matching import coverage, merge_windows, relevance
from tests.helpers import ORDERS, make_office, offer_payload, siret, sign_up

NANCY = (48.6921, 6.1844)
METZ = (49.1193, 6.1757)
STRASBOURG = (48.5734, 7.7521)


def at(days, hours=0):
    return datetime(2030, 1, 1, tzinfo=UTC) + timedelta(days=days, hours=hours)


def test_overlapping_windows_are_merged():
    merged = merge_windows([(at(3), at(5)), (at(0), at(2)), (at(1), at(4))])

    assert merged == [(at(0), at(5))]


def test_coverage_is_the_share_of_the_offer_inside_availabilities():
    windows = merge_windows([(at(0), at(1)), (at(2), at(3))])

    assert coverage(at(0), at(4), windows) == pytest.approx(0.5)
    assert coverage(at(0), at(1), windows) == 1.0
    assert coverage(at(5), at(6), windows) == 0.0
    assert coverage(at(0), at(0), windows) == 0.0


def test_relevance_rewards_proximity_availability_turnover_and_cares():
    best = relevance(0, 50, 1000, 1.0, 1.0)
    worst = relevance(50, 50, 0, 0.0, 0.0)

    assert best == 100 and worst == 0
    assert relevance(10, 50, 500, 1.0, 1.0) > relevance(40, 50, 500, 1.0, 1.0)
    assert relevance(None, 50, 500, 0.5, 0.5) == relevance(25, 50, 500, 0.5, 0.5)


@pytest.fixture
def seeded(pg_client):
    """Trois cabinets (Nancy, Metz, Strasbourg), un remplaçant à Nancy."""
    client = pg_client
    offices = {}
    for index, (name, (lat, lon), order) in enumerate(
        [
            ("nancy", NANCY, ORDERS[0]),
            ("metz", METZ, ORDERS[1]),
            ("strasbourg", STRASBOURG, ORDERS[2]),
        ]
    ):
        owner = sign_up(client, f"{name}@infirmo.example", order, "titulaire")
        office = make_office(
            client,
            owner,
            name=f"Cabinet {name}",
            siret=siret(index + 1),
            latitude=lat,
            longitude=lon,
        )
        offices[name] = (owner, office)
    substitute = sign_up(client, "remplacant@infirmo.example", ORDERS[3])
    return client, offices, substitute


def publish(client, offices, name, **overrides):
    owner, office = offices[name]
    response = client.post(
        f"/api/v1/offices/{office['id']}/offers",
        json=offer_payload(**overrides),
        headers=owner,
    )
    assert response.status_code == 201, response.text
    return response.json()


def search(client, headers, **params):
    response = client.get("/api/v1/offers/search", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_radius_filters_by_real_geographic_distance(seeded):
    client, offices, substitute = seeded
    for name in offices:
        publish(client, offices, name)

    near = search(client, substitute, lat=NANCY[0], lon=NANCY[1], radius_km=60)
    wide = search(client, substitute, lat=NANCY[0], lon=NANCY[1], radius_km=150)

    assert near["total"] == 2
    assert wide["total"] == 3
    distances = {i["distance_km"] for i in near["items"]}
    assert min(distances) < 1 and 45 < max(distances) < 50


def test_distance_sort_orders_by_proximity(seeded):
    client, offices, substitute = seeded
    for name in ("strasbourg", "metz", "nancy"):
        publish(client, offices, name)

    items = search(
        client, substitute, lat=NANCY[0], lon=NANCY[1], radius_km=150, sort="distance"
    )["items"]

    assert [i["distance_km"] for i in items] == sorted(i["distance_km"] for i in items)
    assert items[0]["office_id"] == offices["nancy"][1]["id"]


def test_filters_on_turnover_cares_and_window(seeded, pg_db):
    client, offices, substitute = seeded
    publish(client, offices, "nancy", turnover=300)
    rich = publish(client, offices, "nancy", turnover=900, days_ahead=30)
    base = {"lat": NANCY[0], "lon": NANCY[1], "radius_km": 50}

    assert search(client, substitute, **base, min_turnover=500)["total"] == 1
    soon = (datetime.now(UTC) + timedelta(days=20)).isoformat()
    assert (
        search(client, substitute, **base, window_start=soon)["items"][0]["id"]
        == rich["id"]
    )
    unknown = client.get(
        "/api/v1/offers/search", params={**base, "care": "magie"}, headers=substitute
    )
    assert unknown.status_code == 422 and unknown.json()["code"] == "unknown_care"


def test_care_filter_keeps_offers_requiring_one_of_the_cares(seeded):
    client, offices, substitute = seeded
    publish(client, offices, "nancy", care_codes=["injections"])
    publish(client, offices, "nancy", care_codes=["pansements"], days_ahead=12)
    publish(client, offices, "nancy", days_ahead=14)

    result = search(
        client, substitute, lat=NANCY[0], lon=NANCY[1], radius_km=50, care="injections"
    )

    assert result["total"] == 1


def test_only_open_unexpired_offers_of_other_offices_are_returned(seeded, pg_db):
    from sqlalchemy import text

    client, offices, substitute = seeded
    publish(client, offices, "nancy")
    closed = publish(client, offices, "nancy", days_ahead=12)
    pg_db.execute(
        text("UPDATE offers SET status = 'filled' WHERE id = :id"), {"id": closed["id"]}
    )
    expired = publish(client, offices, "nancy", days_ahead=14)
    pg_db.execute(
        text("UPDATE offers SET valid_till = now() - interval '1 hour' WHERE id = :id"),
        {"id": expired["id"]},
    )
    pg_db.commit()

    result = search(client, substitute, lat=NANCY[0], lon=NANCY[1], radius_km=50)

    assert result["total"] == 1


def test_profile_location_radius_and_cares_are_used_by_default(seeded):
    client, offices, substitute = seeded
    for name in offices:
        publish(client, offices, name)
    client.put(
        "/api/v1/profile",
        json={
            "first_name": "Camille",
            "last_name": "Démo",
            "latitude": NANCY[0],
            "longitude": NANCY[1],
            "radius_km": 60,
        },
        headers=substitute,
    )

    assert search(client, substitute)["total"] == 2


def test_availabilities_raise_the_relevance_score(seeded):
    client, offices, substitute = seeded
    offer = publish(client, offices, "nancy")
    base = {"lat": NANCY[0], "lon": NANCY[1], "radius_km": 50}
    without = search(client, substitute, **base)["items"][0]
    client.post(
        "/api/v1/availabilities",
        json={
            "start_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "end_at": (datetime.now(UTC) + timedelta(days=40)).isoformat(),
        },
        headers=substitute,
    )

    with_window = search(client, substitute, **base)["items"][0]

    assert without["availability"] == 0 and with_window["availability"] == 1
    assert with_window["score"] > without["score"] and with_window["id"] == offer["id"]


def test_search_is_paginated_and_reports_the_total(seeded):
    client, offices, substitute = seeded
    for days in (10, 11, 12):
        publish(client, offices, "nancy", days_ahead=days)

    page = search(
        client,
        substitute,
        lat=NANCY[0],
        lon=NANCY[1],
        radius_km=50,
        limit=2,
        offset=2,
        sort="date",
    )

    assert page["total"] == 3 and len(page["items"]) == 1


def test_search_is_reserved_to_substitutes_and_validates_parameters(seeded):
    client, offices, substitute = seeded
    owner = offices["nancy"][0]

    assert client.get("/api/v1/offers/search", headers=owner).status_code == 403
    assert client.get("/api/v1/offers/search").status_code == 401
    assert (
        client.get(
            "/api/v1/offers/search", params={"lat": 48.0}, headers=substitute
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/offers/search", params={"radius_km": 500}, headers=substitute
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/offers/search", params={"sort": "luck"}, headers=substitute
        ).status_code
        == 422
    )


def test_availability_crud_and_isolation(client):
    mine = sign_up(client, "a@infirmo.example", ORDERS[0])
    theirs = sign_up(client, "b@infirmo.example", ORDERS[1])
    body = {
        "start_at": at(1).isoformat(),
        "end_at": at(2).isoformat(),
    }

    created = client.post("/api/v1/availabilities", json=body, headers=mine)
    assert created.status_code == 201
    assert client.get("/api/v1/availabilities", headers=mine).json()["total"] == 1
    assert client.get("/api/v1/availabilities", headers=theirs).json()["total"] == 0
    url = f"/api/v1/availabilities/{created.json()['id']}"
    assert client.delete(url, headers=theirs).status_code == 404
    assert client.delete(url, headers=mine).status_code == 204


@pytest.mark.parametrize(
    "body",
    [
        {"start_at": at(2).isoformat(), "end_at": at(1).isoformat()},
        {"start_at": at(0).isoformat(), "end_at": at(400).isoformat()},
        {"start_at": "2030-01-01T10:00:00", "end_at": "2030-01-02T10:00:00"},
    ],
)
def test_availability_input_is_validated(client, body):
    headers = sign_up(client, "a@infirmo.example", ORDERS[0])

    assert (
        client.post("/api/v1/availabilities", json=body, headers=headers).status_code
        == 422
    )


def test_titulaires_have_no_availabilities(client):
    owner = sign_up(client, "t@infirmo.example", ORDERS[0], "titulaire")

    assert client.get("/api/v1/availabilities", headers=owner).status_code == 403
