"""`python -m app.export_openapi` : régénère le contrat publié dans docs/api/openapi.json."""

import json
from pathlib import Path

from app.main import app

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"


def render() -> str:
    return (
        json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )


def main() -> None:
    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(render(), encoding="utf-8")


if __name__ == "__main__":
    main()
