"""Hachage scrypt des mots de passe, comparaison en temps constant."""

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024 * 1024
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    salt = bytes.fromhex(encoded.split(":", 1)[0])
    return hmac.compare_digest(hash_password(password, salt), encoded)


# Comparé quand le compte n'existe pas, pour ne pas révéler l'existence d'un email par le temps de réponse.
DUMMY_HASH = hash_password("synthetic-unknown-account")
