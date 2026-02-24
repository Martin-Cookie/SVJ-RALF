"""Tests for units module — routes and services."""


def test_units_list_requires_login(client, db_engine):
    """GET /jednotky should redirect when not authenticated."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User
    import bcrypt

    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    session.add(User(username="u", password_hash=pw, role="admin", display_name="U", is_active=True))
    session.commit()
    session.close()

    resp = client.get("/jednotky", follow_redirects=False)
    assert resp.status_code == 303


def test_units_list_empty(auth_client):
    """GET /jednotky with no units should show empty state."""
    resp = auth_client.get("/jednotky")
    assert resp.status_code == 200
    assert "Jednotky" in resp.text
    assert "Žádné jednotky" in resp.text or "0" in resp.text


def test_units_list_with_data(auth_client, db_engine):
    """GET /jednotky with units should list them."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    session.add(Unit(unit_number=101, building="A", area=55.5))
    session.add(Unit(unit_number=202, building="B", area=72.0))
    session.commit()
    session.close()

    resp = auth_client.get("/jednotky")
    assert resp.status_code == 200
    assert "101" in resp.text
    assert "202" in resp.text


def test_units_search(auth_client, db_engine):
    """GET /jednotky?search= should filter units."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    session.add(Unit(unit_number=101, building="A"))
    session.add(Unit(unit_number=202, building="B"))
    session.commit()
    session.close()

    resp = auth_client.get("/jednotky?search=101")
    assert resp.status_code == 200
    assert "101" in resp.text


def test_unit_detail(auth_client, db_engine):
    """GET /jednotky/{id} should show unit detail."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit

    session = SASession(bind=db_engine)
    unit = Unit(unit_number=101, building="A", area=55.5, section="Sekce 1")
    session.add(unit)
    session.commit()
    unit_id = unit.id
    session.close()

    resp = auth_client.get(f"/jednotky/{unit_id}")
    assert resp.status_code == 200
    assert "101" in resp.text
    assert "55" in resp.text  # area


def test_unit_detail_not_found(auth_client):
    """GET /jednotky/999 should return 404."""
    resp = auth_client.get("/jednotky/999")
    assert resp.status_code == 404


def test_unit_detail_shows_owners(auth_client, db_engine):
    """GET /jednotky/{id} should show linked owners."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická", is_active=True)
    unit = Unit(unit_number=101, building="A")
    session.add_all([owner, unit])
    session.commit()
    ou = OwnerUnit(owner_id=owner.id, unit_id=unit.id)
    session.add(ou)
    session.commit()
    unit_id = unit.id
    session.close()

    resp = auth_client.get(f"/jednotky/{unit_id}")
    assert resp.status_code == 200
    assert "Novák" in resp.text
