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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau, pour les filtres calculés côté application."""
    from math import asin, cos, radians, sin, sqrt

    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(a))
