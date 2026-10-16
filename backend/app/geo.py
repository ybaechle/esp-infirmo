"""Expressions PostGIS sur les colonnes latitude/longitude, sans dépendance supplémentaire."""

from sqlalchemy import cast, func
from sqlalchemy.types import UserDefinedType


class Geography(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw):
        return "geography"


def point(longitude, latitude):
    """Même expression que l'index GiST de la migration : le planificateur doit la reconnaître."""
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography
    )


def within(column_lon, column_lat, lon: float, lat: float, meters: float):
    return func.ST_DWithin(point(column_lon, column_lat), point(lon, lat), meters)


def distance(column_lon, column_lat, lon: float, lat: float):
    return func.ST_Distance(point(column_lon, column_lat), point(lon, lat))
