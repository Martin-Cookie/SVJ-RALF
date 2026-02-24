"""Tests for Backup Restore Variants — Iterace 16, Block H.

Covers: DB file upload restore, folder upload restore.
"""
import io
import os
import zipfile
import sqlite3


def _create_test_db_bytes():
    """Create a minimal SQLite database in memory and return as bytes."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test_table VALUES (1, 'test')")
    conn.commit()

    # Export to bytes
    output = io.BytesIO()
    for line in conn.iterdump():
        output.write(f"{line}\n".encode())
    conn.close()
    output.seek(0)
    return output.read()


def _create_test_db_file():
    """Create a minimal .db file and return as BytesIO."""
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), "test_restore.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test_table VALUES (1, 'test')")
    conn.commit()
    conn.close()

    with open(db_path, "rb") as f:
        content = f.read()
    os.unlink(db_path)

    return io.BytesIO(content)


def test_restore_from_db_file(auth_client):
    """POST /sprava/zaloha/obnovit-soubor accepts a .db file."""
    db_file = _create_test_db_file()
    resp = auth_client.post(
        "/sprava/zaloha/obnovit-soubor",
        files={"file": ("svj.db", db_file, "application/octet-stream")},
        follow_redirects=False,
    )
    # Should redirect or show success (not 404)
    assert resp.status_code in (200, 303), f"Expected 200 or 303, got {resp.status_code}"


def test_restore_from_db_file_requires_admin(reader_client):
    """DB file restore requires admin role."""
    db_file = _create_test_db_file()
    resp = reader_client.post(
        "/sprava/zaloha/obnovit-soubor",
        files={"file": ("svj.db", db_file, "application/octet-stream")},
        follow_redirects=False,
    )
    # _require_admin returns 403 for non-admin authenticated users, 303 redirect for unauthenticated
    assert resp.status_code in (303, 403)


def test_restore_from_db_file_rejects_non_db(auth_client):
    """Restore rejects non-SQLite files."""
    # Use .db extension but non-SQLite content to test magic bytes validation
    fake_file = io.BytesIO(b"this is not a database")
    resp = auth_client.post(
        "/sprava/zaloha/obnovit-soubor",
        files={"file": ("fake.db", fake_file, "application/octet-stream")},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Flash message says "Neplatný soubor — není SQLite databáze."
    assert "neplatn" in resp.text.lower() or "sqlite" in resp.text.lower() or "error" in resp.text.lower()
