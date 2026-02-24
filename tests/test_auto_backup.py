"""Tests for Automatic Backup Config — Iterace 17, Block I.

Covers: auto backup config page, enable/disable, frequency, cleanup.
"""


def test_auto_backup_config_page(auth_client):
    """GET /sprava/auto-zalohy shows config form."""
    resp = auth_client.get("/sprava/auto-zalohy")
    assert resp.status_code == 200
    assert "auto" in resp.text.lower() or "zálohy" in resp.text.lower() or "záloh" in resp.text.lower()


def test_auto_backup_config_requires_admin(reader_client):
    """Auto backup config requires admin role."""
    resp = reader_client.get("/sprava/auto-zalohy", follow_redirects=False)
    assert resp.status_code in (303, 403)


def test_auto_backup_save_config(auth_client):
    """POST /sprava/auto-zalohy saves configuration."""
    resp = auth_client.post(
        "/sprava/auto-zalohy",
        data={"frequency": "daily", "time": "03:00", "max_backups": "5", "is_enabled": "on"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify config was saved by checking the page
    resp2 = auth_client.get("/sprava/auto-zalohy")
    assert resp2.status_code == 200
    assert "03:00" in resp2.text or "daily" in resp2.text


def test_auto_backup_save_weekly(auth_client):
    """Auto backup can be set to weekly frequency."""
    resp = auth_client.post(
        "/sprava/auto-zalohy",
        data={"frequency": "weekly", "time": "22:00", "max_backups": "3", "is_enabled": "on"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_auto_backup_disable(auth_client):
    """Auto backup can be disabled."""
    # First enable
    auth_client.post(
        "/sprava/auto-zalohy",
        data={"frequency": "daily", "time": "02:00", "max_backups": "7", "is_enabled": "on"},
        follow_redirects=False,
    )
    # Then disable (is_enabled not sent = unchecked checkbox)
    resp = auth_client.post(
        "/sprava/auto-zalohy",
        data={"frequency": "daily", "time": "02:00", "max_backups": "7"},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_auto_backup_cleanup(auth_client, db_engine):
    """Auto backup cleanup removes old backups beyond max_backups."""
    import os
    import zipfile
    from app.config import settings

    backup_dir = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    # Create some dummy backup files
    for i in range(5):
        fpath = os.path.join(backup_dir, f"auto_2026020{i}_020000.zip")
        with zipfile.ZipFile(fpath, "w") as zf:
            zf.writestr("test.txt", "test")

    # Set max_backups to 3 and run cleanup via config save
    resp = auth_client.post(
        "/sprava/auto-zalohy",
        data={"frequency": "daily", "time": "02:00", "max_backups": "3", "is_enabled": "on"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Cleanup happens on save — auto_ prefixed backups should be trimmed
    auto_backups = [f for f in os.listdir(backup_dir) if f.startswith("auto_")]
    assert len(auto_backups) <= 3
