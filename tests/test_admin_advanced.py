"""Tests for admin advanced features — Blok C (iter 10).

Covers: data deletion (danger zone), data export, bulk edits.
"""
import io
import zipfile


# --- Data Deletion (Danger Zone) ---


def test_delete_data_page_requires_admin(editor_client):
    """GET /sprava/smazat-data should return 403 for non-admin."""
    resp = editor_client.get("/sprava/smazat-data", follow_redirects=False)
    assert resp.status_code == 403


def test_delete_data_page_requires_login(client):
    """GET /sprava/smazat-data should redirect to login."""
    resp = client.get("/sprava/smazat-data", follow_redirects=False)
    assert resp.status_code == 303


def test_delete_data_page_loads(auth_client):
    """GET /sprava/smazat-data should show danger zone page."""
    resp = auth_client.get("/sprava/smazat-data")
    assert resp.status_code == 200
    assert "Smazání dat" in resp.text


def test_delete_data_requires_confirmation(auth_client):
    """POST /sprava/smazat-data should require DELETE confirmation word."""
    resp = auth_client.post(
        "/sprava/smazat-data",
        data={"categories": "owners", "confirmation": "wrong"},
        follow_redirects=False,
    )
    # Should redirect back with error flash
    assert resp.status_code == 303


def test_delete_data_owners(auth_client, db_engine):
    """POST /sprava/smazat-data with confirmation=DELETE should delete owners."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Test", last_name="Delete", owner_type="physical"))
    session.commit()
    assert session.query(Owner).count() > 0
    session.close()

    resp = auth_client.post(
        "/sprava/smazat-data",
        data={"categories": "owners", "confirmation": "DELETE"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(Owner).count() == 0
    session.close()


def test_delete_data_multiple_categories(auth_client, db_engine):
    """POST /sprava/smazat-data with multiple categories should delete all."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner
    from app.models.common import AuditLog

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Multi", last_name="Del", owner_type="physical"))
    session.add(AuditLog(action="test", model_name="Test"))
    session.commit()
    session.close()

    resp = auth_client.post(
        "/sprava/smazat-data",
        data={"categories": ["owners", "logs"], "confirmation": "DELETE"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(Owner).count() == 0
    # The manually added AuditLog was deleted; only the mass-delete audit entry remains
    assert session.query(AuditLog).filter(AuditLog.action == "test").count() == 0
    session.close()


# --- Data Export ---


def test_export_page_requires_admin(editor_client):
    """GET /sprava/export should return 403 for non-admin."""
    resp = editor_client.get("/sprava/export", follow_redirects=False)
    assert resp.status_code == 403


def test_export_page_loads(auth_client):
    """GET /sprava/export should show export page."""
    resp = auth_client.get("/sprava/export")
    assert resp.status_code == 200
    assert "Export" in resp.text


def test_export_single_category_xlsx(auth_client, db_engine):
    """POST /sprava/export with one category should return xlsx."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Export", last_name="Test", owner_type="physical"))
    session.commit()
    session.close()

    resp = auth_client.post(
        "/sprava/export",
        data={"categories": "owners", "format": "xlsx"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers.get("content-type", "") or \
           "octet-stream" in resp.headers.get("content-type", "")


def test_export_multiple_categories_zip(auth_client, db_engine):
    """POST /sprava/export with multiple categories should return ZIP."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Zip", last_name="Test", owner_type="physical"))
    session.commit()
    session.close()

    resp = auth_client.post(
        "/sprava/export",
        data={"categories": ["owners", "logs"], "format": "xlsx"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "zip" in content_type or "octet-stream" in content_type
    # Verify it's a valid ZIP
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    assert len(z.namelist()) >= 1


def test_export_csv_format(auth_client, db_engine):
    """POST /sprava/export with format=csv should return CSV."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Csv", last_name="Test", owner_type="physical"))
    session.commit()
    session.close()

    resp = auth_client.post(
        "/sprava/export",
        data={"categories": "owners", "format": "csv"},
        follow_redirects=False,
    )
    assert resp.status_code == 200


# --- Bulk Edits ---


def test_bulk_edits_page_requires_admin(editor_client):
    """GET /sprava/hromadne-upravy should return 403 for non-admin."""
    resp = editor_client.get("/sprava/hromadne-upravy", follow_redirects=False)
    assert resp.status_code == 403


def test_bulk_edits_page_loads(auth_client):
    """GET /sprava/hromadne-upravy should show bulk edits page."""
    resp = auth_client.get("/sprava/hromadne-upravy")
    assert resp.status_code == 200
    assert "Hromadné úpravy" in resp.text


def test_bulk_edits_field_values(auth_client, db_engine):
    """GET /sprava/hromadne-upravy?field=space_type should show unique values."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    session.add(Unit(unit_number=1, space_type="Byt", section="A"))
    session.add(Unit(unit_number=2, space_type="Byt", section="B"))
    session.add(Unit(unit_number=3, space_type="Garáž", section="A"))
    session.commit()
    session.close()

    resp = auth_client.get("/sprava/hromadne-upravy?field=space_type")
    assert resp.status_code == 200
    assert "Byt" in resp.text
    assert "Garáž" in resp.text


def test_bulk_edits_apply(auth_client, db_engine):
    """POST /sprava/hromadne-upravy should apply bulk edit."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    u1 = Unit(unit_number=10, space_type="Byt", section="A")
    u2 = Unit(unit_number=11, space_type="Byt", section="A")
    session.add_all([u1, u2])
    session.commit()
    u1_id = u1.id
    u2_id = u2.id
    session.close()

    resp = auth_client.post(
        "/sprava/hromadne-upravy",
        data={
            "field": "space_type",
            "old_value": "Byt",
            "new_value": "Apartmán",
            "unit_ids": [str(u1_id), str(u2_id)],
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    updated = session.query(Unit).filter(Unit.id.in_([u1_id, u2_id])).all()
    for u in updated:
        assert u.space_type == "Apartmán"
    session.close()
