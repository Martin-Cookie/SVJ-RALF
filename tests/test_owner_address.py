"""Tests for Owner Address HTMX editing — Iterace 12, Blok D.

Covers: address edit form, address display, address save for both
perm (trvalá) and corr (korespondenční) prefixes.
"""


def _create_owner(db_engine, **kwargs):
    """Helper to create a test owner."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    defaults = {"first_name": "Test", "last_name": "Address", "owner_type": "physical"}
    defaults.update(kwargs)
    owner = Owner(**defaults)
    session.add(owner)
    session.commit()
    oid = owner.id
    session.close()
    return oid


def test_address_edit_form_perm(auth_client, db_engine):
    """GET /vlastnici/{id}/adresa/perm/upravit-formular returns address form."""
    oid = _create_owner(db_engine)
    resp = auth_client.get(f"/vlastnici/{oid}/adresa/perm/upravit-formular")
    assert resp.status_code == 200
    assert "perm_street" in resp.text or "ulice" in resp.text.lower()


def test_address_edit_form_corr(auth_client, db_engine):
    """GET /vlastnici/{id}/adresa/corr/upravit-formular returns address form."""
    oid = _create_owner(db_engine)
    resp = auth_client.get(f"/vlastnici/{oid}/adresa/corr/upravit-formular")
    assert resp.status_code == 200
    assert "corr_street" in resp.text or "ulice" in resp.text.lower()


def test_address_info_display_perm(auth_client, db_engine):
    """GET /vlastnici/{id}/adresa/perm/info returns address display."""
    oid = _create_owner(db_engine, perm_street="Dlouhá 1", perm_city="Praha", perm_zip="11000")
    resp = auth_client.get(f"/vlastnici/{oid}/adresa/perm/info")
    assert resp.status_code == 200
    assert "Dlouhá 1" in resp.text or "Praha" in resp.text


def test_address_info_display_corr(auth_client, db_engine):
    """GET /vlastnici/{id}/adresa/corr/info returns address display."""
    oid = _create_owner(db_engine, corr_street="Krátká 2", corr_city="Brno", corr_zip="60200")
    resp = auth_client.get(f"/vlastnici/{oid}/adresa/corr/info")
    assert resp.status_code == 200
    assert "Krátká 2" in resp.text or "Brno" in resp.text


def test_address_save_perm(auth_client, db_engine):
    """POST /vlastnici/{id}/adresa/perm/upravit saves permanent address."""
    oid = _create_owner(db_engine)
    resp = auth_client.post(
        f"/vlastnici/{oid}/adresa/perm/upravit",
        data={
            "street": "Nová 42",
            "city": "Praha 1",
            "zip": "11000",
        },
        follow_redirects=False,
    )
    # Should return HTMX partial or redirect
    assert resp.status_code in (200, 303)

    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = session.query(Owner).filter(Owner.id == oid).first()
    assert owner.perm_street == "Nová 42"
    assert owner.perm_city == "Praha 1"
    assert owner.perm_zip == "11000"
    session.close()


def test_address_save_corr(auth_client, db_engine):
    """POST /vlastnici/{id}/adresa/corr/upravit saves correspondence address."""
    oid = _create_owner(db_engine)
    resp = auth_client.post(
        f"/vlastnici/{oid}/adresa/corr/upravit",
        data={
            "street": "Hlavní 10",
            "city": "Brno",
            "zip": "60200",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (200, 303)

    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = session.query(Owner).filter(Owner.id == oid).first()
    assert owner.corr_street == "Hlavní 10"
    assert owner.corr_city == "Brno"
    assert owner.corr_zip == "60200"
    session.close()


def test_address_invalid_prefix_404(auth_client, db_engine):
    """Invalid address prefix returns 404."""
    oid = _create_owner(db_engine)
    resp = auth_client.get(f"/vlastnici/{oid}/adresa/invalid/upravit-formular")
    assert resp.status_code in (400, 404)


def test_address_nonexistent_owner_404(auth_client):
    """Address endpoint for nonexistent owner returns 404."""
    resp = auth_client.get("/vlastnici/99999/adresa/perm/upravit-formular")
    assert resp.status_code == 404
