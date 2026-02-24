"""Tests for voting module — routes and services."""


def test_voting_list_requires_login(client, db_engine):
    """GET /hlasovani should redirect when not authenticated."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User
    import bcrypt

    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    session.add(User(username="u", password_hash=pw, role="admin", display_name="U", is_active=True))
    session.commit()
    session.close()

    resp = client.get("/hlasovani", follow_redirects=False)
    assert resp.status_code == 303


def test_voting_list_empty(auth_client):
    """GET /hlasovani with no votings should show empty state."""
    resp = auth_client.get("/hlasovani")
    assert resp.status_code == 200
    assert "Hlasování" in resp.text


def test_voting_create_page(auth_client):
    """GET /hlasovani/nova should show creation form."""
    resp = auth_client.get("/hlasovani/nova")
    assert resp.status_code == 200
    assert "Nové hlasování" in resp.text


def test_voting_create(auth_client, db_engine):
    """POST /hlasovani/nova should create a new voting."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting

    resp = auth_client.post(
        "/hlasovani/nova",
        data={"name": "Test hlasování", "quorum": "50"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    voting = session.query(Voting).first()
    assert voting is not None
    assert voting.name == "Test hlasování"
    assert voting.status == "koncept"
    session.close()


def test_voting_detail(auth_client, db_engine):
    """GET /hlasovani/{id} should show voting detail."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting

    session = SASession(bind=db_engine)
    v = Voting(name="Test hlasování", status="koncept", quorum=50.0)
    session.add(v)
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.get(f"/hlasovani/{vid}")
    assert resp.status_code == 200
    assert "Test hlasování" in resp.text


def test_voting_detail_not_found(auth_client):
    """GET /hlasovani/999 should return 404."""
    resp = auth_client.get("/hlasovani/999")
    assert resp.status_code == 404


def test_voting_add_item(auth_client, db_engine):
    """POST /hlasovani/{id}/pridat-bod should add an item."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem

    session = SASession(bind=db_engine)
    v = Voting(name="Test", status="koncept", quorum=50.0)
    session.add(v)
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/pridat-bod",
        data={"text": "Schválení rozpočtu"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    items = session.query(VotingItem).filter(VotingItem.voting_id == vid).all()
    assert len(items) == 1
    assert items[0].text == "Schválení rozpočtu"
    session.close()


def test_voting_delete_item(auth_client, db_engine):
    """POST /hlasovani/{id}/smazat-bod/{item_id} should delete an item."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem

    session = SASession(bind=db_engine)
    v = Voting(name="Test", status="koncept", quorum=50.0)
    session.add(v)
    session.flush()
    item = VotingItem(voting_id=v.id, number=1, text="Bod 1")
    session.add(item)
    session.commit()
    vid = v.id
    item_id = item.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/smazat-bod/{item_id}",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    items = session.query(VotingItem).filter(VotingItem.voting_id == vid).all()
    assert len(items) == 0
    session.close()


def test_voting_change_status(auth_client, db_engine):
    """POST /hlasovani/{id}/stav should change voting status."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting

    session = SASession(bind=db_engine)
    v = Voting(name="Test", status="koncept", quorum=50.0)
    session.add(v)
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/stav",
        data={"status": "aktivní"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    v = session.query(Voting).filter(Voting.id == vid).first()
    assert v.status == "aktivní"
    session.close()


def test_voting_delete(auth_client, db_engine):
    """POST /hlasovani/{id}/smazat should cascade-delete voting."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem

    session = SASession(bind=db_engine)
    v = Voting(name="Test", status="koncept", quorum=50.0)
    session.add(v)
    session.flush()
    session.add(VotingItem(voting_id=v.id, number=1, text="Bod"))
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/smazat",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(Voting).filter(Voting.id == vid).first() is None
    assert session.query(VotingItem).filter(VotingItem.voting_id == vid).count() == 0
    session.close()


def test_voting_filter_by_status(auth_client, db_engine):
    """GET /hlasovani?status=koncept should filter votings."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting

    session = SASession(bind=db_engine)
    session.add(Voting(name="Koncept", status="koncept", quorum=50.0))
    session.add(Voting(name="Aktivní", status="aktivní", quorum=50.0))
    session.commit()
    session.close()

    resp = auth_client.get("/hlasovani?status=koncept")
    assert resp.status_code == 200
    assert "Koncept" in resp.text
