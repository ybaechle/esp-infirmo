import pytest

from app.export_openapi import CONTRACT, render
from app.main import app


def test_published_contract_matches_the_code():
    assert CONTRACT.exists(), (
        "lancer `uv run python -m app.export_openapi` depuis backend/"
    )
    assert CONTRACT.read_text(encoding="utf-8") == render(), (
        "docs/api/openapi.json est périmé : relancer `uv run python -m app.export_openapi`"
    )


def test_every_v1_operation_is_tagged_and_declares_the_common_errors():
    schema = app.openapi()
    for path, operations in schema["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in operations.items():
            assert operation.get("tags"), f"{method.upper()} {path} sans tag"
            assert {"401", "422", "503"} <= set(operation["responses"]), (
                f"{method.upper()} {path}"
            )


def test_error_body_schema_is_the_one_clients_receive():
    error = app.openapi()["components"]["schemas"]["ErrorBody"]

    assert set(error["properties"]) == {"detail", "code"} and error["required"] == [
        "detail"
    ]


def test_tags_used_by_routes_are_described():
    schema = app.openapi()
    described = {tag["name"] for tag in schema["tags"]}
    used = {
        tag
        for path, operations in schema["paths"].items()
        if path.startswith("/api/v1/")
        for operation in operations.values()
        for tag in operation.get("tags", [])
    }

    assert used <= described


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_interactive_documentation_is_served(path):
    from fastapi.testclient import TestClient

    assert TestClient(app).get(path).status_code == 200
