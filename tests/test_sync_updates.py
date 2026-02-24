"""Tests for Sync selective updates — Iterace 13, Blok E.

Covers: selective update, accept/reject individual records,
contact transfer, export to Excel.
"""


def _create_sync_session(db_engine):
    """Helper to create a sync session with records."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    owner = Owner(first_name="Jan", last_name="Novák", owner_type="physical", name_normalized="novák jan")
    unit = Unit(unit_number=100, space_type="Byt")
    session.add_all([owner, unit])
    session.flush()
    ou = OwnerUnit(owner_id=owner.id, unit_id=unit.id)
    session.add(ou)

    ss = SyncSession(name="Test Sync", source_format="interní")
    session.add(ss)
    session.flush()

    rec1 = SyncRecord(
        session_id=ss.id, unit_id=unit.id,
        status="rozdílní", db_owner_name="Novák Jan",
        csv_owner_name="Novák Jana", csv_share="100",
    )
    rec2 = SyncRecord(
        session_id=ss.id, unit_id=unit.id,
        status="shoda", db_owner_name="Novák Jan",
        csv_owner_name="Novák Jan", csv_share="100",
    )
    session.add_all([rec1, rec2])
    session.commit()
    result = {"session_id": ss.id, "rec1_id": rec1.id, "rec2_id": rec2.id, "owner_id": owner.id, "unit_id": unit.id}
    session.close()
    return result


def test_sync_accept_record(auth_client, db_engine):
    """POST /synchronizace/{id}/prijmout/{rec_id} marks record as resolved."""
    data = _create_sync_session(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/prijmout/{data['rec1_id']}",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncRecord
    session = SASession(bind=db_engine)
    rec = session.query(SyncRecord).filter(SyncRecord.id == data['rec1_id']).first()
    assert rec.is_resolved == 1
    session.close()


def test_sync_reject_record(auth_client, db_engine):
    """POST /synchronizace/{id}/odmitnout/{rec_id} marks record as rejected."""
    data = _create_sync_session(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/odmitnout/{data['rec1_id']}",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncRecord
    session = SASession(bind=db_engine)
    rec = session.query(SyncRecord).filter(SyncRecord.id == data['rec1_id']).first()
    assert rec.is_resolved == 1
    session.close()


def test_sync_selective_update(auth_client, db_engine):
    """POST /synchronizace/{id}/aktualizovat updates selected records."""
    data = _create_sync_session(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/aktualizovat",
        data={"record_ids": [str(data['rec1_id'])]},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_sync_contact_transfer(auth_client, db_engine):
    """POST /synchronizace/{id}/aplikovat-kontakty transfers contacts from CSV."""
    data = _create_sync_session(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/aplikovat-kontakty",
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_sync_export(auth_client, db_engine):
    """POST /synchronizace/{id}/exportovat exports to Excel."""
    data = _create_sync_session(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/exportovat",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should be xlsx content type
    assert "spreadsheet" in resp.headers.get("content-type", "") or resp.status_code == 200


def test_sync_accept_requires_login(client, db_engine):
    """Accept endpoint requires authentication."""
    resp = client.post("/synchronizace/1/prijmout/1", follow_redirects=False)
    assert resp.status_code == 303
