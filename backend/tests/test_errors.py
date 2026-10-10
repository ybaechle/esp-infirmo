from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import ApiError
from app.main import app as real_app


def test_api_error_exposes_stable_code_and_keeps_detail_shape():
    app = FastAPI()
    app.exception_handlers.update(real_app.exception_handlers)

    @app.get("/conflict")
    def conflict():
        raise ApiError(409, "email_taken", "Email already used", {"X-Reason": "dup"})

    response = TestClient(app).get("/conflict")

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already used", "code": "email_taken"}
    assert response.headers["x-reason"] == "dup"
