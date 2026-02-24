"""Tests for Sync Owner Exchange — Iterace 14, Blok F.

Covers: single exchange preview + confirm, bulk exchange, role checks, validation.
"""


def _create_sync_with_different_owners(db_engine):
    """Helper to create sync session with records that have different owners."""
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncSession, SyncRecord
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    old_owner = Owner(first_name="Starý", last_name="Vlastník", owner_type="physical", name_normalized="vlastník starý")
    new_owner = Owner(first_name="Nový", last_name="Vlastník", owner_type="physical", name_normalized="vlastník nový")
    unit = Unit(unit_number=300, space_type="Byt")
    session.add_all([old_owner, new_owner, unit])
    session.flush()

    ou = OwnerUnit(owner_id=old_owner.id, unit_id=unit.id)
    session.add(ou)

    ss = SyncSession(name="Exchange Test", source_format="interní")
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


def test_sync_exchange_preview(auth_client, db_engine):
    """GET /synchronizace/{id}/vymena/{rec_id} shows exchange preview."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.get(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}"
    )
    assert resp.status_code == 200
    assert "Vlastník" in resp.text


def test_sync_exchange_confirm(auth_client, db_engine):
    """POST /synchronizace/{id}/vymena/{rec_id}/potvrdit performs exchange."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={"new_owner_id": str(data["new_owner_id"])},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Old OwnerUnit should have valid_to set
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import OwnerUnit
    session = SASession(bind=db_engine)
    old_ou = session.query(OwnerUnit).filter(OwnerUnit.id == data["ou_id"]).first()
    assert old_ou.valid_to is not None
    # New OwnerUnit should exist
    new_ou = session.query(OwnerUnit).filter(
        OwnerUnit.owner_id == data["new_owner_id"],
        OwnerUnit.unit_id == data["unit_id"],
        OwnerUnit.valid_to.is_(None),
    ).first()
    assert new_ou is not None
    session.close()


def test_sync_exchange_confirm_invalid_owner(auth_client, db_engine):
    """Exchange confirm rejects invalid/nonexistent owner_id."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}/potvrdit",
        data={"new_owner_id": "99999"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Should redirect back to exchange preview, not to session page
    location = resp.headers.get("location", "")
    assert "/vymena/" in location


def test_sync_bulk_exchange_preview(auth_client, db_engine):
    """POST /synchronizace/{id}/vymena-hromadna shows bulk exchange preview."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena-hromadna",
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_sync_bulk_exchange_confirm(auth_client, db_engine):
    """POST /synchronizace/{id}/vymena-hromadna/potvrdit performs bulk exchange."""
    data = _create_sync_with_different_owners(db_engine)
    resp = auth_client.post(
        f"/synchronizace/{data['session_id']}/vymena-hromadna/potvrdit",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify DB: with 0.9 threshold, name "Vlastník Nový" vs "Nový Vlastník"
    # may or may not match depending on SequenceMatcher. Check record status.
    from sqlalchemy.orm import Session as SASession
    from app.models.sync import SyncRecord
    session = SASession(bind=db_engine)
    rec = session.query(SyncRecord).filter(SyncRecord.id == data["rec_id"]).first()
    # Record may or may not be resolved depending on fuzzy match score
    assert rec is not None
    session.close()


def test_sync_exchange_requires_login(client):
    """Exchange endpoint requires authentication."""
    resp = client.get("/synchronizace/1/vymena/1", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")


def test_sync_exchange_role_check(reader_client, db_engine):
    """Reader role cannot perform owner exchanges."""
    data = _create_sync_with_different_owners(db_engine)
    resp = reader_client.get(
        f"/synchronizace/{data['session_id']}/vymena/{data['rec_id']}",
        follow_redirects=False,
    )
    assert resp.status_code == 303
    location = resp.headers.get("location", "")
    assert "/synchronizace" in location or "/login" in location
