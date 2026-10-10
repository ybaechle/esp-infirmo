"""Erreurs applicatives : le format `{"detail": …}` existant, enrichi d'un `code` stable."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    """Erreur métier dont `code` est exploitable par le mobile sans lire le message."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code, message, headers)
        self.code = code


async def api_error_handler(request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )
