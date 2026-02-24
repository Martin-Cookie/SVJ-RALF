"""Tests for owners module — routes and services."""


def _make_owner(**kwargs):
    """Helper to create Owner with required fields."""
    from app.models.owner import Owner
    defaults = {
        "first_name": "Jan",
        "last_name": "Novák",
        "name_with_titles": "Novák Jan",
        "name_normalized": "novak jan",
        "owner_type": "physical",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Owner(**defaults)


def test_owners_list_requires_login(client, db_engine):
    """GET /vlastnici should redirect when not authenticated."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User
    import bcrypt

    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    session.add(User(username="u", password_hash=pw, role="admin", display_name="U", is_active=True))
    session.commit()
    session.close()

    resp = client.get("/vlastnici", follow_redirects=False)
    assert resp.status_code == 303


def test_owners_list_empty(auth_client):
    """GET /vlastnici with no owners should show empty state."""
    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    assert "Vlastníci" in resp.text
    assert "Žádní vlastníci" in resp.text or "0" in resp.text


def test_owners_list_with_data(auth_client, db_engine):
    """GET /vlastnici with owners should list them."""
    from sqlalchemy.orm import Session as SASession

    session = SASession(bind=db_engine)
    session.add(_make_owner(first_name="Jan", last_name="Novák"))
    session.add(_make_owner(first_name="Firma", last_name="s.r.o.", name_with_titles="s.r.o. Firma", name_normalized="s.r.o. firma", owner_type="legal"))
    session.commit()
    session.close()

    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    assert "Novák" in resp.text
    assert "s.r.o." in resp.text


def test_owners_search(auth_client, db_engine):
    """GET /vlastnici?search= should filter owners."""
    from sqlalchemy.orm import Session as SASession

    session = SASession(bind=db_engine)
    session.add(_make_owner(first_name="Jan", last_name="Novák"))
    session.add(_make_owner(first_name="Eva", last_name="Svobodová", name_with_titles="Svobodová Eva", name_normalized="svobodova eva"))
    session.commit()
    session.close()

    resp = auth_client.get("/vlastnici?search=Novák")
    assert resp.status_code == 200
    assert "Novák" in resp.text


def test_owners_filter_by_type(auth_client, db_engine):
    """GET /vlastnici?typ= should filter by owner type."""
    from sqlalchemy.orm import Session as SASession

    session = SASession(bind=db_engine)
    session.add(_make_owner(first_name="Jan", last_name="Novák"))
    session.add(_make_owner(first_name="Firma", last_name="s.r.o.", name_with_titles="s.r.o. Firma", name_normalized="s.r.o. firma", owner_type="legal"))
    session.commit()
    session.close()

    resp = auth_client.get("/vlastnici?typ=physical")
    assert resp.status_code == 200
    assert "Novák" in resp.text


def test_owner_detail(auth_client, db_engine):
    """GET /vlastnici/{id} should show owner detail."""
    from sqlalchemy.orm import Session as SASession

    session = SASession(bind=db_engine)
    owner = _make_owner(email="jan@test.cz")
    session.add(owner)
    session.commit()
    owner_id = owner.id
    session.close()

    resp = auth_client.get(f"/vlastnici/{owner_id}")
    assert resp.status_code == 200
    assert "Novák" in resp.text
    assert "jan@test.cz" in resp.text


def test_owner_detail_not_found(auth_client):
    """GET /vlastnici/999 should return 404."""
    resp = auth_client.get("/vlastnici/999")
    assert resp.status_code == 404


def test_owner_update_contact(auth_client, db_engine):
    """POST /vlastnici/{id}/upravit should update owner contact info."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = _make_owner()
    session.add(owner)
    session.commit()
    owner_id = owner.id
    session.close()

    resp = auth_client.post(
        f"/vlastnici/{owner_id}/upravit",
        data={"email": "novy@email.cz", "phone": "+420123456789"},
        follow_redirects=False,
    )
    assert resp.status_code == 303 or resp.status_code == 200

    # Verify updated
    session = SASession(bind=db_engine)
    updated = session.query(Owner).get(owner_id)
    assert updated.email == "novy@email.cz"
    session.close()


def test_owner_add_unit(auth_client, db_engine):
    """POST /vlastnici/{id}/jednotky/pridat should link a unit."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Unit, OwnerUnit

    session = SASession(bind=db_engine)
    owner = _make_owner()
    unit = Unit(unit_number=101, building_number="A")
    session.add_all([owner, unit])
    session.commit()
    owner_id = owner.id
    unit_id = unit.id
    session.close()

    resp = auth_client.post(
        f"/vlastnici/{owner_id}/jednotky/pridat",
        data={"unit_id": str(unit_id)},
        follow_redirects=False,
    )
    assert resp.status_code == 303 or resp.status_code == 200

    session = SASession(bind=db_engine)
    ou = session.query(OwnerUnit).filter_by(owner_id=owner_id, unit_id=unit_id).first()
    assert ou is not None
    session.close()


def test_excel_export(auth_client, db_engine):
    """GET /vlastnici/export should return an Excel file."""
    from sqlalchemy.orm import Session as SASession

    session = SASession(bind=db_engine)
    session.add(_make_owner())
    session.commit()
    session.close()

    resp = auth_client.get("/vlastnici/export")
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers.get("content-type", "") or "octet-stream" in resp.headers.get("content-type", "")
