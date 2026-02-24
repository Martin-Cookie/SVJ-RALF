"""Tests for sync module — Blok 7."""


def test_sync_list_requires_login(client):
    """GET /synchronizace should redirect to login for unauthenticated users."""
    resp = client.get("/synchronizace", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")


def test_sync_list_empty(auth_client):
    """GET /synchronizace should show empty state when no sync sessions exist."""
    resp = auth_client.get("/synchronizace")
    assert resp.status_code == 200
    assert "Synchronizace" in resp.text


def test_sync_upload_page(auth_client):
    """GET /synchronizace/nova should show upload form."""
    resp = auth_client.get("/synchronizace/nova")
    assert resp.status_code == 200
    assert "form" in resp.text.lower()


def test_sync_upload_csv(auth_client, db_engine):
    """POST /synchronizace/nova should create a sync session from CSV."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner, Unit, OwnerUnit

    # Create test data in DB
    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", name_with_titles="Novák Jan", name_normalized="novak jan", owner_type="physical")
    unit = Unit(unit_number=101, building_number="A", floor_area=50.0)
    session.add_all([owner, unit])
    session.flush()
    session.add(OwnerUnit(owner_id=owner.id, unit_id=unit.id, share=1.0, votes=100))
    session.commit()
    session.close()

    # Upload CSV
    csv_content = b"jednotka;vlastnik;podil\n101;Jan Nov\xc3\xa1k;1/1\n"
    resp = auth_client.post(
        "/synchronizace/nova",
        data={"name": "Test sync"},
        files=[("file", ("test.csv", csv_content, "text/csv"))],
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/synchronizace/" in resp.headers.get("location", "")


def test_sync_detail(auth_client, db_engine):
    """GET /synchronizace/{id} should show comparison results."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord

    session = SASession(bind=db_engine)
    ss = SyncSession(name="Test sync", source_format="interní")
    session.add(ss)
    session.flush()
    session.add(SyncRecord(
        session_id=ss.id, status="shoda",
        db_owner_name="Jan Novák", csv_owner_name="Jan Novák",
        db_share="1/1", csv_share="1/1",
    ))
    session.add(SyncRecord(
        session_id=ss.id, status="rozdílní",
        db_owner_name="Eva Malá", csv_owner_name="Petr Velký",
        db_share="1/2", csv_share="1/2",
    ))
    session.commit()
    ss_id = ss.id
    session.close()

    resp = auth_client.get(f"/synchronizace/{ss_id}")
    assert resp.status_code == 200
    assert "Jan Novák" in resp.text
    assert "Test sync" in resp.text


def test_sync_detail_filter(auth_client, db_engine):
    """GET /synchronizace/{id}?status=shoda should filter by status."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord

    session = SASession(bind=db_engine)
    ss = SyncSession(name="Filter test")
    session.add(ss)
    session.flush()
    session.add(SyncRecord(
        session_id=ss.id, status="shoda",
        db_owner_name="Jan Novák", csv_owner_name="Jan Novák",
    ))
    session.add(SyncRecord(
        session_id=ss.id, status="rozdílní",
        db_owner_name="Eva Malá", csv_owner_name="Petr Velký",
    ))
    session.commit()
    ss_id = ss.id
    session.close()

    resp = auth_client.get(f"/synchronizace/{ss_id}?status=shoda")
    assert resp.status_code == 200
    assert "Jan Novák" in resp.text


def test_sync_delete(auth_client, db_engine):
    """POST /synchronizace/{id}/smazat should delete a sync session."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession

    session = SASession(bind=db_engine)
    ss = SyncSession(name="Delete test")
    session.add(ss)
    session.commit()
    ss_id = ss.id
    session.close()

    resp = auth_client.post(f"/synchronizace/{ss_id}/smazat", follow_redirects=False)
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(SyncSession).filter(SyncSession.id == ss_id).first() is None
    session.close()


def test_sync_detail_not_found(auth_client):
    """GET /synchronizace/9999 should return 404."""
    resp = auth_client.get("/synchronizace/9999")
    assert resp.status_code == 404
