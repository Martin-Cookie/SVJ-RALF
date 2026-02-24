"""Tests for Owner Advanced Filters + Back URL chain — Iterace 16, Block H.

Covers: ownership type filter, contact filters, back URL preservation.
"""


def _create_owners_with_variety(db_engine):
    """Create owners with different types, contacts, ownership types."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    # Owner with email + phone + SJM
    o1 = Owner(first_name="Jan", last_name="Novák", owner_type="physical",
               name_normalized="novák jan", email="jan@test.cz", phone="123456789")
    # Owner with email, no phone, VL
    o2 = Owner(first_name="Marie", last_name="Svobodová", owner_type="physical",
               name_normalized="svobodová marie", email="marie@test.cz", phone="")
    # Owner with phone, no email, SJVL
    o3 = Owner(first_name="Pavel", last_name="Dvořák", owner_type="physical",
               name_normalized="dvořák pavel", email="", phone="987654321")
    # Owner with no contact
    o4 = Owner(first_name="Firma", last_name="s.r.o.", owner_type="legal",
               name_normalized="firma s.r.o.", email="", phone="")

    unit = Unit(unit_number=600, space_type="Byt")
    session.add_all([o1, o2, o3, o4, unit])
    session.flush()

    # Different ownership types
    ou1 = OwnerUnit(owner_id=o1.id, unit_id=unit.id, ownership_type="SJM")
    ou2 = OwnerUnit(owner_id=o2.id, unit_id=unit.id, ownership_type="VL")
    ou3 = OwnerUnit(owner_id=o3.id, unit_id=unit.id, ownership_type="SJVL")
    session.add_all([ou1, ou2, ou3])
    session.commit()

    result = {
        "o1_id": o1.id, "o2_id": o2.id, "o3_id": o3.id, "o4_id": o4.id,
        "unit_id": unit.id,
    }
    session.close()
    return result


def test_filter_by_ownership_type(auth_client, db_engine):
    """Filter owners by ownership type (SJM, VL, SJVL)."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?vlastnictvi=SJM")
    assert resp.status_code == 200
    assert "Novák" in resp.text
    # SJM filter should exclude owners with different ownership types
    assert "Dvořák" not in resp.text  # SJVL, not SJM
    assert "Firma" not in resp.text  # no ownership link at all


def test_filter_by_ownership_type_vl(auth_client, db_engine):
    """Filter by VL ownership type."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?vlastnictvi=VL")
    assert resp.status_code == 200
    assert "Svobodová" in resp.text
    assert "Novák" not in resp.text  # SJM, not VL


def test_filter_with_email(auth_client, db_engine):
    """Filter owners that have email."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?kontakt=s_emailem")
    assert resp.status_code == 200
    # Both Jan (has email) and Marie (has email) should appear
    assert "Novák" in resp.text
    assert "Svobodová" in resp.text
    # Owners without email should be excluded
    assert "Firma" not in resp.text


def test_filter_without_email(auth_client, db_engine):
    """Filter owners that have no email."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?kontakt=bez_emailu")
    assert resp.status_code == 200
    # Pavel (no email) and Firma (no email) should appear
    assert "Dvořák" in resp.text
    assert "Firma" in resp.text
    # Owners with email should be excluded
    assert "Novák" not in resp.text
    assert "Svobodová" not in resp.text


def test_filter_with_phone(auth_client, db_engine):
    """Filter owners that have phone."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?kontakt=s_telefonem")
    assert resp.status_code == 200
    # Jan (has phone) and Pavel (has phone)
    assert "Novák" in resp.text
    assert "Dvořák" in resp.text
    # Owners without phone should be excluded
    assert "Svobodová" not in resp.text
    assert "Firma" not in resp.text


def test_filter_without_phone(auth_client, db_engine):
    """Filter owners that have no phone."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?kontakt=bez_telefonu")
    assert resp.status_code == 200
    # Marie (no phone) and Firma (no phone)
    assert "Svobodová" in resp.text
    assert "Firma" in resp.text
    # Owners with phone should be excluded
    assert "Novák" not in resp.text
    assert "Dvořák" not in resp.text


def test_filter_combination(auth_client, db_engine):
    """Multiple filters combined: physical + has email."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici?typ=physical&kontakt=s_emailem")
    assert resp.status_code == 200
    # Physical + has email: Jan and Marie
    assert "Novák" in resp.text
    assert "Svobodová" in resp.text
    # Legal entity excluded by type filter
    assert "Firma" not in resp.text


def test_back_url_preserved_on_detail(auth_client, db_engine):
    """Detail page preserves back URL with filters."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get(
        f"/vlastnici/{data['o1_id']}?back_url=/vlastnici?typ=physical%26kontakt=s_emailem"
    )
    assert resp.status_code == 200
    # The back link href should contain the filter URL
    assert "typ=physical" in resp.text


def test_owner_list_filter_bubbles_show_counts(auth_client, db_engine):
    """Filter bubbles should show counts for contact types."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    # Should show contact filter bubbles
    text = resp.text.lower()
    assert "email" in text
    assert "telefon" in text


def test_ownership_type_dropdown_shows(auth_client, db_engine):
    """Ownership type dropdown appears when ownership types exist."""
    data = _create_owners_with_variety(db_engine)
    resp = auth_client.get("/vlastnici")
    assert resp.status_code == 200
    # Should show ownership type options in the dropdown
    assert "SJM" in resp.text
    assert "VL" in resp.text
    assert "SJVL" in resp.text
