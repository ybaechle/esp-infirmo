import base64

import pytest
from sqlalchemy import String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.crypto import (
    DecryptionError,
    EncryptedText,
    EncryptionUnavailable,
    decrypt,
    encrypt,
)


def key(byte: bytes) -> str:
    return base64.b64encode(byte * 32).decode()


def test_roundtrip_hides_the_plaintext_and_randomizes_each_output(encryption_keys):
    first = encrypt(b"secret patient note", b"ctx")
    second = encrypt(b"secret patient note", b"ctx")

    assert b"secret" not in first and first != second
    assert decrypt(first, b"ctx") == b"secret patient note"


def test_tampering_or_moving_the_ciphertext_is_detected(encryption_keys):
    blob = encrypt(b"data", b"messages.content")

    with pytest.raises(DecryptionError):
        decrypt(blob, b"transmissions.text")
    with pytest.raises(DecryptionError):
        decrypt(blob[:-1] + bytes([blob[-1] ^ 1]), b"messages.content")
    with pytest.raises(DecryptionError):
        decrypt(b"not-encrypted", b"messages.content")


def test_rotation_encrypts_with_the_newest_key_and_still_reads_old_data(monkeypatch):
    monkeypatch.setenv("INFIRMO_ENCRYPTION_KEYS", f"old:{key(b'a')}")
    old = encrypt(b"before rotation")
    monkeypatch.setenv("INFIRMO_ENCRYPTION_KEYS", f"new:{key(b'b')},old:{key(b'a')}")

    new = encrypt(b"after rotation")

    assert decrypt(old) == b"before rotation" and decrypt(new) == b"after rotation"
    assert b"new" in new[:10] and b"old" in old[:10]
    monkeypatch.setenv("INFIRMO_ENCRYPTION_KEYS", f"new:{key(b'b')}")
    with pytest.raises(DecryptionError):
        decrypt(old)


@pytest.mark.parametrize(
    "value",
    ["", "id-sans-cle", f"id:{'!' * 8}", "id:" + base64.b64encode(b"court").decode()],
)
def test_missing_or_invalid_keys_refuse_to_encrypt(monkeypatch, value):
    monkeypatch.setenv("INFIRMO_ENCRYPTION_KEYS", value)

    with pytest.raises(EncryptionUnavailable):
        encrypt(b"data")


def test_missing_variable_refuses_to_encrypt(monkeypatch):
    monkeypatch.delenv("INFIRMO_ENCRYPTION_KEYS", raising=False)

    with pytest.raises(EncryptionUnavailable):
        encrypt(b"data")


def test_encrypted_text_column_stores_ciphertext_and_reads_plaintext(encryption_keys):
    class Base(DeclarativeBase):
        pass

    class Note(Base):
        __tablename__ = "notes"
        id: Mapped[int] = mapped_column(primary_key=True)
        body: Mapped[str | None] = mapped_column(EncryptedText("notes.body"))
        label: Mapped[str | None] = mapped_column(String(10))

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Note(id=1, body="douleur thoracique"), Note(id=2, body=None)])
        db.commit()
        stored = db.execute(text("SELECT body FROM notes WHERE id = 1")).scalar()
        assert "douleur" not in stored
        assert db.scalar(select(Note.body).where(Note.id == 1)) == "douleur thoracique"
        assert db.scalar(select(Note.body).where(Note.id == 2)) is None
