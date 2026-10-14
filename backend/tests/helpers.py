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
