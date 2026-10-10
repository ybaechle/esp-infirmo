"""Pagination `limit`/`offset` commune à toutes les listes de l'API."""

from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")

MAX_LIMIT = 100


class PageParams(BaseModel):
    limit: int = 20
    offset: int = 0


def page_params(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


Pagination = Annotated[PageParams, Depends(page_params)]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


def paginate(db: Session, statement: Select, params: PageParams) -> Page:
    """Un `ORDER BY` déterministe est requis dans `statement` pour une pagination stable."""
    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    items = db.scalars(statement.limit(params.limit).offset(params.offset)).all()
    return Page(
        items=list(items), total=total, limit=params.limit, offset=params.offset
    )
