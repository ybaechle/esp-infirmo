import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Integer, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from app.pagination import Page, Pagination, paginate


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(Item(id=i) for i in range(1, 8))
        db.commit()

    app = FastAPI()

    @app.get("/items", response_model=Page[int])
    def items(params: Pagination):
        with Session(engine) as db:
            page = paginate(db, select(Item.id).order_by(Item.id), params)
        return page

    return TestClient(app)


def test_returns_requested_window_with_total(client):
    body = client.get("/items", params={"limit": 3, "offset": 2}).json()

    assert body == {"items": [3, 4, 5], "total": 7, "limit": 3, "offset": 2}


def test_defaults_and_last_partial_page(client):
    assert client.get("/items").json()["limit"] == 20
    assert client.get("/items", params={"limit": 5, "offset": 5}).json()["items"] == [
        6,
        7,
    ]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}]
)
def test_rejects_out_of_range_parameters(client, params):
    assert client.get("/items", params=params).status_code == 422
