"""Tests for SVJ Address CRUD + Member Edit — Iterace 13, Blok E.

Covers: SVJ address add/edit/delete, board member edit.
"""


def test_svj_address_add(auth_client, db_engine):
    """POST /sprava/adresa/pridat creates an SVJ address."""
    resp = auth_client.post(
        "/sprava/adresa/pridat",
        data={"street": "Hlavní 1", "city": "Praha", "zip_code": "11000"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.administration import SvjAddress
    session = SASession(bind=db_engine)
    addr = session.query(SvjAddress).filter(SvjAddress.street == "Hlavní 1").first()
    assert addr is not None
    assert addr.city == "Praha"
    session.close()


def test_svj_address_edit(auth_client, db_engine):
    """POST /sprava/adresa/{id}/upravit updates an SVJ address."""
    from sqlalchemy.orm import Session as SASession
    from app.models.administration import SvjAddress
    session = SASession(bind=db_engine)
    addr = SvjAddress(street="Old Street", city="Old City", zip_code="00000")
    session.add(addr)
    session.commit()
    addr_id = addr.id
    session.close()

    resp = auth_client.post(
        f"/sprava/adresa/{addr_id}/upravit",
        data={"street": "New Street", "city": "New City", "zip_code": "99999"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    updated = session.query(SvjAddress).filter(SvjAddress.id == addr_id).first()
    assert updated.street == "New Street"
    assert updated.city == "New City"
    session.close()


def test_svj_address_delete(auth_client, db_engine):
    """POST /sprava/adresa/{id}/smazat deletes an SVJ address."""
    from sqlalchemy.orm import Session as SASession
    from app.models.administration import SvjAddress
    session = SASession(bind=db_engine)
    addr = SvjAddress(street="Delete Me", city="City", zip_code="12345")
    session.add(addr)
    session.commit()
    addr_id = addr.id
    session.close()

    resp = auth_client.post(
        f"/sprava/adresa/{addr_id}/smazat",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    deleted = session.query(SvjAddress).filter(SvjAddress.id == addr_id).first()
    assert deleted is None
    session.close()


def test_member_edit(auth_client, db_engine):
    """POST /sprava/clen/{id}/upravit updates board member."""
    from sqlalchemy.orm import Session as SASession
    from app.models.administration import BoardMember
    session = SASession(bind=db_engine)
    member = BoardMember(name="Old Name", role="Člen", group="board")
    session.add(member)
    session.commit()
    mid = member.id
    session.close()

    resp = auth_client.post(
        f"/sprava/clen/{mid}/upravit",
        data={"name": "New Name", "role": "Předseda", "email": "new@test.cz", "phone": "123456"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    updated = session.query(BoardMember).filter(BoardMember.id == mid).first()
    assert updated.name == "New Name"
    assert updated.role == "Předseda"
    session.close()


def test_svj_address_requires_admin(client, db_engine):
    """SVJ address endpoints require admin access."""
    resp = client.post(
        "/sprava/adresa/pridat",
        data={"street": "X", "city": "Y", "zip_code": "Z"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
