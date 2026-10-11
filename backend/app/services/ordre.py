"""Vérification du numéro d'inscription à l'Ordre des infirmiers (RPPS, 11 chiffres)."""

from typing import Protocol


class OrdreUnavailable(Exception):
    """Le service de vérification n'a pas répondu : l'inscription est refusée, pas devinée."""


class OrdreVerifier(Protocol):
    def is_valid(self, order_number: str) -> bool: ...


def luhn_valid(number: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class MockOrdreVerifier:
    """Mock de développement (F1.3) : même règle de forme que le RPPS réel, sans appel réseau."""

    def is_valid(self, order_number: str) -> bool:
        return (
            len(order_number) == 11
            and order_number.isdigit()
            and luhn_valid(order_number)
        )


def get_ordre_verifier() -> OrdreVerifier:
    return MockOrdreVerifier()
