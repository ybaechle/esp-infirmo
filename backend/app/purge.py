"""`python -m app.purge` : applique les durées de conservation et affiche les volumes supprimés."""

import json

from sqlalchemy.orm import Session

from app.database import get_engine
from app.services.purge import purge


def main() -> None:
    with Session(get_engine()) as db:
        print(json.dumps(purge(db)))


if __name__ == "__main__":
    main()
