"""Client du microservice IA privé (F5.1).

Contrat attendu côté `ia/` (à confirmer avec son responsable) :
`POST {INFIRMO_IA_URL}/transcribe`, corps = audio brut avec son `Content-Type`,
réponse 200 `{"text": "..."}`. Le service n'est joignable que sur le réseau interne ;
il ne reçoit jamais d'identifiant d'utilisateur ni de patient.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

TIMEOUT_SECONDS = 20
MAX_RESPONSE = 256 * 1024
MAX_TRANSCRIPT = 20_000


class IaUnavailable(Exception):
    """Service absent, en erreur, trop lent ou réponse inexploitable."""


class IaClient(Protocol):
    def transcribe(self, audio: bytes, content_type: str) -> str: ...


class HttpIaClient:
    def __init__(self, base_url: str, timeout: float = TIMEOUT_SECONDS):
        self.url = base_url.rstrip("/") + "/transcribe"
        self.timeout = timeout

    def transcribe(self, audio: bytes, content_type: str) -> str:
        request = urllib.request.Request(
            self.url, data=audio, headers={"Content-Type": content_type}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise IaUnavailable
            text = json.loads(body)["text"]
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            raise IaUnavailable from error
        if not isinstance(text, str) or len(text) > MAX_TRANSCRIPT:
            raise IaUnavailable
        return text.strip()


def get_ia_client() -> IaClient | None:
    url = os.environ.get("INFIRMO_IA_URL")
    return HttpIaClient(url) if url else None
