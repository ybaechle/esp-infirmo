"""Point d'extension du push mobile (FCM/APNs).

Aucun fournisseur n'est branché : en ajouter un exige une revue de résidence des données et
un contrat de sous-traitance (AGENTS.md). Les alertes passent par la boîte de notifications
et le WebSocket. Un message push ne contiendrait de toute façon qu'un texte générique.
"""

from typing import Protocol


class PushSender(Protocol):
    def send(self, platform: str, token: str, title: str, body: str) -> None: ...


def get_push_sender() -> PushSender | None:
    return None
