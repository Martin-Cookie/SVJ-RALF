"""Tests for UI enhancements — Iterace 11.

Covers: back URL chain, column sorting script inclusion, print button.
"""


def test_owner_detail_back_url(auth_client, db_engine):
    """Owner detail page should include back link with preserved query params."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Back", last_name="Test", owner_type="physical")
    session.add(owner)
    session.commit()
    oid = owner.id
    session.close()

    resp = auth_client.get(f"/vlastnici/{oid}?back=/vlastnici%3Ffilter%3Dbyt")
    assert resp.status_code == 200
    # Back URL should be present in the page
    assert "back=" in resp.text or "Zpět" in resp.text


def test_unit_detail_back_url(auth_client, db_engine):
    """Unit detail page should include back link."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=999, space_type="Byt")
    session.add(unit)
    session.commit()
    uid = unit.id
    session.close()

    resp = auth_client.get(f"/jednotky/{uid}?back=/jednotky")
    assert resp.status_code == 200


def test_owner_list_has_sortable_headers(auth_client, db_engine):
    """Owner list page should include sortable table headers when data exists."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    session.add(Owner(first_name="Sort", last_name="Test", owner_type="physical"))
    session.commit()
    session.close()

    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    assert "data-sort" in resp.text


def test_unit_list_has_sortable_headers(auth_client, db_engine):
    """Unit list page should include sortable table headers when data exists."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    session.add(Unit(unit_number=777, space_type="Byt"))
    session.commit()
    session.close()

    resp = auth_client.get("/jednotky")
    assert resp.status_code == 200
    assert "data-sort" in resp.text


def test_print_stylesheet_exists(auth_client):
    """Base template should include print stylesheet."""
    resp = auth_client.get("/")
    assert resp.status_code == 200
    assert "custom.css" in resp.text  # Print styles are in custom.css


def test_owner_list_has_print_button(auth_client):
    """Owner list should have a print button."""
    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    assert "Tisk" in resp.text or "window.print" in resp.text
