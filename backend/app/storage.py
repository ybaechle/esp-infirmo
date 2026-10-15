"""Stockage des fichiers sur disque : contenu toujours chiffré, nom choisi par le serveur."""

import os
import re
import uuid
from pathlib import Path

from app.crypto import decrypt, encrypt

KEY_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _root() -> Path:
    root = Path(os.environ.get("INFIRMO_STORAGE_DIR", "storage"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(key: str) -> Path:
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError("Invalid storage key")
    return _root() / key


def put(data: bytes, context: bytes) -> str:
    key = uuid.uuid4().hex
    target = _path(key)
    temporary = target.with_suffix(".tmp")
    temporary.write_bytes(encrypt(data, context))
    temporary.replace(target)
    return key


def get(key: str, context: bytes) -> bytes:
    return decrypt(_path(key).read_bytes(), context)


def delete(key: str) -> None:
    _path(key).unlink(missing_ok=True)
