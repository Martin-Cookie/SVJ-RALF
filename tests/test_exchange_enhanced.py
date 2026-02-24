"""Tests for Enhanced Owner Exchange — Iterace 15, Block G.

Covers: date picker, AuditLog/ImportLog for exchange operations.
"""
from datetime import date


def _create_sync_with_different_owners(db_engine):
    """Helper to create sync session with records that have different owners."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    old_owner = Owner(first_name="Starý", last_name="Vlastník", owner_type="physical", name_normalized="vlastník starý")
    new_owner = Owner(first_name="Nový", last_name="Vlastník", owner_type="physical", name_normalized="vlastník nový")
    unit = Unit(unit_number=400, space_type="Byt")
    session.add_all([old_owner, new_owner, unit])
    session.flush()

    ou = OwnerUnit(owner_id=old_owner.id, unit_id=unit.id)
    session.add(ou)

    ss = SyncSession(name="Exchange Date Test", source_format="interní")
    session.add(ss)
    session.flush()

    rec = SyncRecord(
        session_id=ss.id, unit_id=unit.id,
        status="rozdílní",
        db_owner_name="Vlastník Starý",
        csv_owner_name="Vlastník Nový",
    )
    session.add(rec)
    session.commit()

    result = {
        "session_id": ss.id, "rec_id": rec.id,
        "old_owner_id": old_owner.id, "new_owner_id": new_owner.id,
        "unit_id": unit.id, "ou_id": ou.id,
    }
    session.close()
    return result


def test_exchange_with_custom_date(auth_client, db_engine):
    """Exchange confirm accepts custom exchange_date from form."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={
            "new_owner_id": str(data["new_owner_id"]),
            "exchange_date": "2025-06-15",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify: old OU valid_to = 2025-06-15, new OU valid_from = 2025-06-15
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import OwnerUnit
    session = SASession(bind=db_engine)
    old_ou = session.query(OwnerUnit).filter(OwnerUnit.id == data["ou_id"]).first()
    assert old_ou.valid_to == date(2025, 6, 15)

    new_ou = session.query(OwnerUnit).filter(
        OwnerUnit.owner_id == data["new_owner_id"],
        OwnerUnit.unit_id == data["unit_id"],
    ).first()
    assert new_ou is not None
    assert new_ou.valid_from == date(2025, 6, 15)
    session.close()


def test_exchange_default_date_is_today(auth_client, db_engine):
    """Exchange confirm without exchange_date uses today."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={"new_owner_id": str(data["new_owner_id"])},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.owner import OwnerUnit
    session = SASession(bind=db_engine)
    old_ou = session.query(OwnerUnit).filter(OwnerUnit.id == data["ou_id"]).first()
    assert old_ou.valid_to == date.today()
    session.close()


def test_exchange_creates_audit_log(auth_client, db_engine):
    """Exchange confirm creates AuditLog entry."""
    data = _create_sync_with_different_owners(db_engine)
    auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={"new_owner_id": str(data["new_owner_id"])},
        follow_redirects=False,
    )

    from sqlalchemy.orm import Session as SASession
    from app.models.common import AuditLog
    session = SASession(bind=db_engine)
    logs = session.query(AuditLog).filter(
        AuditLog.action == "exchange",
        AuditLog.model_name == "OwnerUnit",
    ).all()
    assert len(logs) >= 1
    # Should contain unit info
    log = logs[0]
    assert str(data["unit_id"]) in (log.old_value or "") or str(data["unit_id"]) in (log.new_value or "")
    session.close()


def test_exchange_creates_import_log(auth_client, db_engine):
    """Exchange confirm creates ImportLog entry."""
    data = _create_sync_with_different_owners(db_engine)
    auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={"new_owner_id": str(data["new_owner_id"])},
        follow_redirects=False,
    )

    from sqlalchemy.orm import Session as SASession
    from app.models.common import ImportLog
    session = SASession(bind=db_engine)
    logs = session.query(ImportLog).filter(ImportLog.source == "exchange").all()
    assert len(logs) >= 1
    assert logs[0].records_count == 1
    assert logs[0].status == "success"
    session.close()


def test_exchange_preview_shows_date_picker(auth_client, db_engine):
    """Exchange preview page should include a date input."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.get(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}"
    )
    assert resp.status_code == 200
    assert 'type="date"' in resp.text or 'exchange_date' in resp.text


def test_bulk_exchange_creates_audit_logs(auth_client, db_engine):
    """Bulk exchange confirm creates AuditLog entries for exact matches."""
    # Create data with exact-match names (score >= 0.9)
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)
    old_owner = Owner(first_name="Pavel", last_name="Černý", owner_type="physical", name_normalized="černý pavel")
    new_owner = Owner(first_name="Karel", last_name="Bílý", owner_type="physical", name_normalized="bílý karel")
    unit = Unit(unit_number=500, space_type="Byt")
    session.add_all([old_owner, new_owner, unit])
    session.flush()

    ou = OwnerUnit(owner_id=old_owner.id, unit_id=unit.id)
    session.add(ou)

    ss = SyncSession(name="Bulk Audit Test", source_format="interní")
    session.add(ss)
    session.flush()

    # csv_owner_name matches new_owner.display_name exactly ("Bílý Karel")
    rec = SyncRecord(
        session_id=ss.id, unit_id=unit.id,
        status="rozdílní",
        db_owner_name="Černý Pavel",
        csv_owner_name="Bílý Karel",  # Exact match to new_owner.display_name
    )
    session.add(rec)
    session.commit()
    session_id = ss.id
    session.close()

    auth_client.post(
        f"/synchronizace/{session_id}/vymena-hromadna/potvrdit",
        follow_redirects=False,
    )

    from app.models.common import AuditLog
    session = SASession(bind=db_engine)
    logs = session.query(AuditLog).filter(
        AuditLog.action == "exchange",
        AuditLog.model_name == "OwnerUnit",
    ).all()
    assert len(logs) >= 1, "Bulk exchange should create AuditLog for exact matches"
    session.close()
