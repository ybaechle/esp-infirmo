"""Chiffrement AES-256-GCM au repos, avec trousseau de clés pour la rotation (F6.2).

`INFIRMO_ENCRYPTION_KEYS` = `id:base64,id:base64` ; la première clé chiffre, toutes déchiffrent.
Pour tourner une clé : ajouter la nouvelle en tête, conserver l'ancienne tant que des données
l'utilisent. Le format `INF1 | len(id) | id | nonce | texte chiffré+tag` est donc auto-descriptif.
"""

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

MAGIC = b"INF1"
NONCE_SIZE = 12


class EncryptionUnavailable(Exception):
    """Aucune clé valide n'est configurée : on refuse de stocker en clair."""


class DecryptionError(Exception):
    """Donnée altérée, mauvais contexte ou clé inconnue."""


def _keyring() -> list[tuple[str, bytes]]:
    raw = os.environ.get("INFIRMO_ENCRYPTION_KEYS", "")
    ring = []
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        key_id, _, encoded = entry.partition(":")
        try:
            key = base64.b64decode(encoded, validate=True)
        except binascii.Error:
            raise EncryptionUnavailable from None
        if not key_id or len(key_id) > 32 or len(key) != 32:
            raise EncryptionUnavailable
        ring.append((key_id, key))
    if not ring:
        raise EncryptionUnavailable
    return ring


def encrypt(plaintext: bytes, context: bytes = b"") -> bytes:
    """`context` lie le chiffré à son usage (table, colonne) : un chiffré déplacé ne se lit plus."""
    key_id, key = _keyring()[0]
    nonce = os.urandom(NONCE_SIZE)
    sealed = AESGCM(key).encrypt(nonce, plaintext, context)
    kid = key_id.encode()
    return MAGIC + bytes([len(kid)]) + kid + nonce + sealed


def decrypt(blob: bytes, context: bytes = b"") -> bytes:
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 1:
        raise DecryptionError
    id_len = blob[len(MAGIC)]
    start = len(MAGIC) + 1
    key_id = blob[start : start + id_len].decode(errors="replace")
    nonce = blob[start + id_len : start + id_len + NONCE_SIZE]
    sealed = blob[start + id_len + NONCE_SIZE :]
    key = dict(_keyring()).get(key_id)
    if key is None or len(nonce) != NONCE_SIZE:
        raise DecryptionError
    try:
        return AESGCM(key).decrypt(nonce, sealed, context)
    except InvalidTag:
        raise DecryptionError from None


class EncryptedText(TypeDecorator):
    """Colonne texte chiffrée de façon transparente ; `context` = `table.colonne`."""

    impl = Text
    cache_ok = True

    def __init__(self, context: str):
        super().__init__()
        self.context = context.encode()

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return base64.b64encode(encrypt(value.encode(), self.context)).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt(base64.b64decode(value), self.context).decode()
