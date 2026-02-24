"""Tests for Voting Proxy (plné moci) — Iterace 17, Block I.

Covers: proxy assignment, proxy list, proxy delete, proxy vote delegation.
"""


def _create_voting_with_owners(db_engine):
    """Create a voting with 2 owners and ballots."""
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Owner, Unit, OwnerUnit
    from app.models.voting import Voting, VotingItem, Ballot

    session = SASession(bind=db_engine)

    o1 = Owner(first_name="Jan", last_name="Novák", owner_type="physical", name_normalized="novák jan")
    o2 = Owner(first_name="Marie", last_name="Svobodová", owner_type="physical", name_normalized="svobodová marie")
    unit1 = Unit(unit_number=101, space_type="Byt")
    unit2 = Unit(unit_number=102, space_type="Byt")
    session.add_all([o1, o2, unit1, unit2])
    session.flush()

    ou1 = OwnerUnit(owner_id=o1.id, unit_id=unit1.id, ownership_type="VL")
    ou2 = OwnerUnit(owner_id=o2.id, unit_id=unit2.id, ownership_type="VL")
    session.add_all([ou1, ou2])
    session.flush()

    voting = Voting(name="Test hlasování", status="active")
    session.add(voting)
    session.flush()

    item = VotingItem(voting_id=voting.id, text="Bod 1", number=1)
    session.add(item)
    session.flush()

    b1 = Ballot(voting_id=voting.id, owner_id=o1.id, unit_id=unit1.id)
    b2 = Ballot(voting_id=voting.id, owner_id=o2.id, unit_id=unit2.id)
    session.add_all([b1, b2])
    session.commit()

    result = {
        "voting_id": voting.id, "o1_id": o1.id, "o2_id": o2.id,
        "unit1_id": unit1.id, "unit2_id": unit2.id,
        "b1_id": b1.id, "b2_id": b2.id,
    }
    session.close()
    return result


def test_proxy_page(auth_client, db_engine):
    """GET /hlasovani/{id}/plne-moci shows proxy management page."""
    data = _create_voting_with_owners(db_engine)
    resp = auth_client.get(f"/hlasovani/{data['voting_id']}/plne-moci")
    assert resp.status_code == 200
    assert "pln" in resp.text.lower() or "moc" in resp.text.lower() or "proxy" in resp.text.lower()


def test_proxy_add(auth_client, db_engine):
    """POST /hlasovani/{id}/plne-moci/pridat assigns a proxy."""
    data = _create_voting_with_owners(db_engine)
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o2_id"])},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_proxy_add_self_rejected(auth_client, db_engine):
    """Cannot assign proxy to self."""
    data = _create_voting_with_owners(db_engine)
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o1_id"])},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should show error
    text = resp.text.lower()
    assert "chyb" in text or "nelze" in text or "error" in text or "shodný" in text


def test_proxy_delete(auth_client, db_engine):
    """DELETE proxy removes delegation."""
    data = _create_voting_with_owners(db_engine)
    # First add proxy
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o2_id"])},
        follow_redirects=False,
    )

    # Check proxy list
    from sqlalchemy.orm import Session as SASession
    from app.models.owner import Proxy
    session = SASession(bind=db_engine)
    proxy = session.query(Proxy).first()
    assert proxy is not None
    proxy_id = proxy.id
    session.close()

    # Delete proxy
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/{proxy_id}/smazat",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify deleted
    session = SASession(bind=db_engine)
    assert session.query(Proxy).filter(Proxy.id == proxy_id).first() is None
    session.close()


def test_proxy_shows_in_list(auth_client, db_engine):
    """Proxy appears in the voting proxy list."""
    data = _create_voting_with_owners(db_engine)
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o2_id"])},
        follow_redirects=False,
    )

    resp = auth_client.get(f"/hlasovani/{data['voting_id']}/plne-moci")
    assert resp.status_code == 200
    assert "Novák" in resp.text
    assert "Svobodová" in resp.text


def test_proxy_requires_login(client, db_engine):
    """Proxy page requires authentication."""
    resp = client.get("/hlasovani/1/plne-moci", follow_redirects=False)
    assert resp.status_code == 303


def test_proxy_duplicate_rejected(auth_client, db_engine):
    """Cannot add two proxies from the same grantor."""
    data = _create_voting_with_owners(db_engine)
    # Add first proxy
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o2_id"])},
        follow_redirects=False,
    )
    # Try to add duplicate
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/plne-moci/pridat",
        data={"grantor_id": str(data["o1_id"]), "grantee_id": str(data["o2_id"])},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    text = resp.text.lower()
    assert "delegoval" in text or "již" in text or "chyb" in text


def test_proxy_requires_editor_role(reader_client, db_engine):
    """Proxy management requires editor or admin role."""
    data = _create_voting_with_owners(db_engine)
    # Reader should be blocked
    resp = reader_client.get(
        f"/hlasovani/{data['voting_id']}/plne-moci",
        follow_redirects=False,
    )
    assert resp.status_code in (303, 403)
