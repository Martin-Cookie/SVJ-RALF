"""Tests for audit log and backup/restore — Blok B (iter 10)."""
import os
import zipfile


# --- Audit Log ---


def test_audit_page_requires_admin(editor_client):
    """GET /sprava/audit should return 403 for non-admin."""
    resp = editor_client.get("/sprava/audit", follow_redirects=False)
    assert resp.status_code == 403


def test_audit_page_requires_login(client):
    """GET /sprava/audit should redirect to login."""
    resp = client.get("/sprava/audit", follow_redirects=False)
    assert resp.status_code == 303


def test_audit_page_empty(auth_client):
    """GET /sprava/audit should show empty audit log."""
    resp = auth_client.get("/sprava/audit")
    assert resp.status_code == 200
    assert "Audit log" in resp.text


def test_audit_page_shows_entries(auth_client, db_engine):
    """GET /sprava/audit should show audit entries."""
    from sqlalchemy.orm import Session as SASession
    from app.models.common import AuditLog

    session = SASession(bind=db_engine)
    log = AuditLog(
        user_id=1,
        action="update",
        model_name="Owner",
        record_id=42,
        field_name="email",
        old_value="old@test.cz",
        new_value="new@test.cz",
    )
    session.add(log)
    session.commit()
    session.close()

    resp = auth_client.get("/sprava/audit")
    assert resp.status_code == 200
    assert "Owner" in resp.text
    assert "email" in resp.text


def test_audit_page_filter_by_action(auth_client, db_engine):
    """GET /sprava/audit?action=create should filter by action."""
    from sqlalchemy.orm import Session as SASession
    from app.models.common import AuditLog

    session = SASession(bind=db_engine)
    session.add(AuditLog(action="create", model_name="Owner", record_id=1))
    session.add(AuditLog(action="delete", model_name="Unit", record_id=2))
    session.commit()
    session.close()

    resp = auth_client.get("/sprava/audit?action=create")
    assert resp.status_code == 200
    assert "Owner" in resp.text


# --- Backup ---


def test_backup_create(auth_client):
    """POST /sprava/zaloha/vytvorit should create a ZIP backup."""
    resp = auth_client.post(
        "/sprava/zaloha/vytvorit",
        data={"name": "test-backup"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_backup_create_requires_admin(editor_client):
    """POST /sprava/zaloha/vytvorit should require admin."""
    resp = editor_client.post(
        "/sprava/zaloha/vytvorit",
        data={"name": "hacker"},
        follow_redirects=False,
    )
    assert resp.status_code == 403


def test_backup_list(auth_client):
    """GET /sprava/zalohy should show backup list."""
    resp = auth_client.get("/sprava/zalohy")
    assert resp.status_code == 200
    assert "Zálohy" in resp.text


def test_backup_download(auth_client):
    """Create a backup then download it."""
    # Create
    auth_client.post(
        "/sprava/zaloha/vytvorit",
        data={"name": "download-test"},
        follow_redirects=False,
    )

    # List backups to find the filename
    resp = auth_client.get("/sprava/zalohy")
    assert resp.status_code == 200
    assert "download-test" in resp.text


def test_backup_delete(auth_client):
    """Create a backup, then delete it."""
    auth_client.post(
        "/sprava/zaloha/vytvorit",
        data={"name": "delete-test"},
        follow_redirects=False,
    )

    # Find the backup file
    from app.config import settings
    backup_dir = os.path.join(settings.UPLOAD_DIR, "..", "backups")
    if os.path.exists(backup_dir):
        files = [f for f in os.listdir(backup_dir) if "delete-test" in f]
        if files:
            resp = auth_client.post(
                f"/sprava/zaloha/{files[0]}/smazat",
                follow_redirects=False,
            )
            assert resp.status_code == 303


def test_safe_backup_path_rejects_traversal():
    """_safe_backup_path should reject path traversal attempts."""
    from app.routers.admin import _safe_backup_path

    # These should all return None (rejected)
    assert _safe_backup_path("../etc/passwd.zip") is None
    assert _safe_backup_path("..%2Fetc.zip") is None
    assert _safe_backup_path("foo/../bar.zip") is None
    assert _safe_backup_path("/etc/passwd.zip") is None
    assert _safe_backup_path("valid_name.txt") is None  # not .zip

    # Valid filenames should return a path
    result = _safe_backup_path("backup_20240101.zip")
    assert result is not None
    assert result.endswith("backup_20240101.zip")


def test_backup_restore_requires_admin(editor_client):
    """POST /sprava/zaloha/obnovit should require admin."""
    import io
    resp = editor_client.post(
        "/sprava/zaloha/obnovit",
        files={"file": ("test.zip", io.BytesIO(b"fake"), "application/zip")},
        follow_redirects=False,
    )
    assert resp.status_code == 403
