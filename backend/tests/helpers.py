from tests.test_register import PASSWORD, payload

# Numéros RPPS fictifs valides (somme de Luhn), un par compte de test.
ORDERS = ["12345678903", "98765432103", "10000000009", "20000000008", "30000000007"]


def sign_up(client, email, order=ORDERS[0], role="remplacant"):
    response = client.post(
        "/api/v1/auth/register",
        json=payload(email=email, order_number=order, role=role),
    )
    assert response.status_code == 201, response.text
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()
    return {"Authorization": "Bearer " + tokens["access_token"]}


def user_id(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


OFFICE = {
    "name": "Cabinet des Lilas",
    "siret": "73282932000074",
    "address": "12 rue Stanislas",
    "postcode": "54000",
    "city": "Nancy",
    "latitude": 48.6937,
    "longitude": 6.1834,
}


def make_office(client, headers, **overrides):
    response = client.post(
        "/api/v1/offices", json={**OFFICE, **overrides}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def offer_payload(days_ahead=10, **overrides):
    from datetime import UTC, datetime, timedelta

    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=days_ahead)
    body = {
        "description": "Tournée du matin, 12 patients.",
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=5)).isoformat(),
        "valid_till": (start - timedelta(days=2)).isoformat(),
        "turnover": 600,
        "care_codes": [],
    }
    return {**body, **overrides}
