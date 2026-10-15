import pytest
from sqlalchemy import select, update

from app.models import Document, User
from tests.helpers import ORDERS, sign_up

PDF = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch, encryption_keys):
    monkeypatch.setenv("INFIRMO_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def auth(client):
    return sign_up(client, "camille@infirmo.example", ORDERS[0])


@pytest.fixture
def other(client):
    return sign_up(client, "autre@infirmo.example", ORDERS[1])


@pytest.fixture
def admin(client, db):
    headers = sign_up(client, "admin@infirmo.example", ORDERS[2], "titulaire")
    db.execute(
        update(User).where(User.email == "admin@infirmo.example").values(is_admin=True)
    )
    db.commit()
    return headers


def upload(
    client,
    headers,
    content=PDF,
    doc_type="carte_pro",
    name="scan.pdf",
    mime="application/pdf",
):
    return client.post(
        "/api/v1/documents",
        data={"doc_type": doc_type},
        files={"file": (name, content, mime)},
        headers=headers,
    )


def test_upload_stores_an_encrypted_file_under_a_server_chosen_name(
    client, auth, storage_dir
):
    response = upload(client, auth, name="../../etc/passwd.html")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending" and body["size"] == len(PDF)
    files = list(storage_dir.iterdir())
    assert len(files) == 1 and len(files[0].name) == 32 and files[0].suffix == ""
    assert b"%PDF" not in files[0].read_bytes()


def test_content_decides_not_the_declared_type(client, auth):
    html = upload(client, auth, content=b"<html><script>alert(1)</script></html>")
    spoofed = upload(
        client, auth, content=b"MZ\x90\x00", name="x.pdf", mime="application/pdf"
    )

    assert html.status_code == spoofed.status_code == 422
    assert html.json()["code"] == "not_a_pdf"


def test_files_over_five_megabytes_are_refused(client, auth, storage_dir):
    big = b"%PDF-" + b"0" * (5 * 1024 * 1024)

    response = upload(client, auth, content=big)

    assert response.status_code == 413 and response.json()["code"] == "file_too_large"
    assert list(storage_dir.iterdir()) == []


def test_unknown_document_type_is_refused(client, auth):
    assert upload(client, auth, doc_type="passeport").status_code == 422


def test_upload_requires_authentication(client):
    assert upload(client, {}).status_code == 401


def test_replacing_a_document_resets_review_and_removes_the_old_file(
    client, auth, admin, db, storage_dir
):
    first = upload(client, auth).json()
    client.patch(
        f"/api/v1/admin/documents/{first['id']}",
        json={"status": "approved"},
        headers=admin,
    )
    before = {p.name for p in storage_dir.iterdir()}

    second = upload(client, auth, content=PDF + b"v2").json()

    assert second["id"] == first["id"] and second["status"] == "pending"
    after = {p.name for p in storage_dir.iterdir()}
    assert len(after) == 1 and after != before
    assert len(db.scalars(select(Document)).all()) == 1


def test_owner_downloads_the_original_bytes_with_safe_headers(client, auth):
    document = upload(client, auth).json()

    response = client.get(f"/api/v1/documents/{document['id']}/file", headers=auth)

    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in response.headers["content-disposition"]


def test_other_users_cannot_read_but_admins_can(client, auth, other, admin):
    document = upload(client, auth).json()
    url = f"/api/v1/documents/{document['id']}/file"

    assert client.get(url, headers=other).status_code == 404
    assert client.get(url, headers=admin).content == PDF


def test_listing_is_limited_to_own_documents(client, auth, other):
    upload(client, auth)
    upload(client, auth, doc_type="rib")
    upload(client, other)

    mine = client.get("/api/v1/documents", headers=auth).json()

    assert [d["doc_type"] for d in mine] == ["carte_pro", "rib"]


def test_delete_removes_row_and_file_and_is_owner_only(
    client, auth, other, storage_dir
):
    document = upload(client, auth).json()
    url = f"/api/v1/documents/{document['id']}"

    assert client.delete(url, headers=other).status_code == 404
    assert client.delete(url, headers=auth).status_code == 204
    assert list(storage_dir.iterdir()) == []
    assert client.get(f"{url}/file", headers=auth).status_code == 404


def test_admin_reviews_pending_documents(client, auth, admin):
    document = upload(client, auth).json()

    pending = client.get("/api/v1/admin/documents", headers=admin).json()
    reviewed = client.patch(
        f"/api/v1/admin/documents/{document['id']}",
        json={"status": "rejected"},
        headers=admin,
    )

    assert pending["total"] == 1
    assert reviewed.json()["status"] == "rejected"
    assert client.get("/api/v1/admin/documents", headers=admin).json()["total"] == 0


def test_review_is_admin_only_and_validated(client, auth, admin):
    document = upload(client, auth).json()
    url = f"/api/v1/admin/documents/{document['id']}"

    assert (
        client.patch(url, json={"status": "approved"}, headers=auth).status_code == 403
    )
    assert (
        client.patch(url, json={"status": "pending"}, headers=admin).status_code == 422
    )
    assert (
        client.patch(
            "/api/v1/admin/documents/00000000-0000-0000-0000-000000000000",
            json={"status": "approved"},
            headers=admin,
        ).status_code
        == 404
    )


def test_without_an_encryption_key_nothing_is_stored(
    client, auth, monkeypatch, storage_dir
):
    monkeypatch.delenv("INFIRMO_ENCRYPTION_KEYS")

    response = upload(client, auth)

    assert (
        response.status_code == 503
        and response.json()["code"] == "encryption_unavailable"
    )
    assert list(storage_dir.iterdir()) == []
