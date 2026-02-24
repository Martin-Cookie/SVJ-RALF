"""Tests for Unit CRUD — Iterace 12, Blok D.

Covers: unit create (form + POST), unit edit (HTMX form + display + save),
unit delete with cascade.
"""


def test_unit_create_form_htmx(auth_client):
    """GET /jednotky/nova-formular should return HTMX form partial."""
    resp = auth_client.get("/jednotky/nova-formular")
    assert resp.status_code == 200
    assert "unit_number" in resp.text


def test_unit_create_form_requires_login(client):
    """Create form requires authentication."""
    resp = client.get("/jednotky/nova-formular")
    assert resp.status_code in (200, 303)
    # Empty response or redirect for unauthenticated
    if resp.status_code == 200:
        assert resp.text == "" or "login" in resp.text.lower()


def test_unit_create(auth_client, db_engine):
    """POST /jednotky/nova creates a new unit."""
    resp = auth_client.post(
        "/jednotky/nova",
        data={
            "unit_number": "1234",
            "building_number": "1098",
            "space_type": "Byt",
            "section": "A",
            "floor_area": "65.5",
            "room_count": "3+1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = session.query(Unit).filter(Unit.unit_number == 1234).first()
    assert unit is not None
    assert unit.building_number == "1098"
    assert unit.space_type == "Byt"
    assert unit.floor_area == 65.5
    session.close()


def test_unit_create_duplicate_number(auth_client, db_engine):
    """Creating a unit with duplicate number should fail gracefully."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    session.add(Unit(unit_number=9999, space_type="Byt"))
    session.commit()
    session.close()

    resp = auth_client.post(
        "/jednotky/nova",
        data={"unit_number": "9999", "space_type": "Byt"},
        follow_redirects=False,
    )
    # Should redirect with error flash
    assert resp.status_code == 303


def test_unit_edit_form_htmx(auth_client, db_engine):
    """GET /jednotky/{id}/upravit-formular returns HTMX edit form."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=5555, space_type="Byt")
    session.add(unit)
    session.commit()
    uid = unit.id
    session.close()

    resp = auth_client.get(f"/jednotky/{uid}/upravit-formular")
    assert resp.status_code == 200
    assert "unit_number" in resp.text or "5555" in resp.text


def test_unit_info_display_htmx(auth_client, db_engine):
    """GET /jednotky/{id}/info returns HTMX display partial."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=5556, space_type="Garáž")
    session.add(unit)
    session.commit()
    uid = unit.id
    session.close()

    resp = auth_client.get(f"/jednotky/{uid}/info")
    assert resp.status_code == 200
    assert "5556" in resp.text or "Garáž" in resp.text


def test_unit_update(auth_client, db_engine):
    """POST /jednotky/{id}/upravit updates unit fields."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=5557, space_type="Byt", floor_area=50.0)
    session.add(unit)
    session.commit()
    uid = unit.id
    session.close()

    resp = auth_client.post(
        f"/jednotky/{uid}/upravit",
        data={
            "unit_number": "5557",
            "space_type": "Nebytový prostor",
            "floor_area": "75.3",
            "room_count": "2+kk",
            "building_number": "1099",
            "section": "B",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    updated = session.query(Unit).filter(Unit.id == uid).first()
    assert updated.space_type == "Nebytový prostor"
    assert updated.floor_area == 75.3
    assert updated.room_count == "2+kk"
    session.close()


def test_unit_delete(auth_client, db_engine):
    """POST /jednotky/{id}/smazat deletes unit."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=5558, space_type="Byt")
    session.add(unit)
    session.commit()
    uid = unit.id
    session.close()

    resp = auth_client.post(
        f"/jednotky/{uid}/smazat",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    deleted = session.query(Unit).filter(Unit.id == uid).first()
    assert deleted is None
    session.close()


def test_unit_delete_cascades_owner_units(auth_client, db_engine):
    """Deleting a unit cascades to OwnerUnit links."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Cascade", last_name="Test", owner_type="physical")
    unit = Unit(unit_number=5559, space_type="Byt")
    session.add_all([owner, unit])
    session.flush()
    ou = OwnerUnit(owner_id=owner.id, unit_id=unit.id)
    session.add(ou)
    session.commit()
    uid = unit.id
    ou_id = ou.id
    session.close()

    resp = auth_client.post(f"/jednotky/{uid}/smazat", follow_redirects=False)
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    link = session.query(OwnerUnit).filter(OwnerUnit.id == ou_id).first()
    assert link is None
    session.close()
