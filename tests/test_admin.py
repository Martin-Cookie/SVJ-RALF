"""Tests for administration module — Blok 8."""


def test_admin_requires_login(client):
    """GET /sprava should redirect to login for unauthenticated users."""
    resp = client.get("/sprava", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")


def test_admin_page(auth_client):
    """GET /sprava should show admin page."""
    resp = auth_client.get("/sprava")
    assert resp.status_code == 200
    assert "Správa" in resp.text


def test_admin_update_svj_info(auth_client, db_engine):
    """POST /sprava/info should update SVJ info."""
    resp = auth_client.post(
        "/sprava/info",
        data={"name": "SVJ Test", "building_type": "Bytový dům", "total_shares": "1000"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.administration import SvjInfo
    session = SASession(bind=db_engine)
    info = session.query(SvjInfo).first()
    assert info is not None
    assert info.name == "SVJ Test"
    session.close()


def test_admin_add_board_member(auth_client, db_engine):
    """POST /sprava/clen should add a board member."""
    resp = auth_client.post(
        "/sprava/clen",
        data={"name": "Jan Novák", "role": "Předseda", "group": "board"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.administration import BoardMember
    session = SASession(bind=db_engine)
    member = session.query(BoardMember).first()
    assert member is not None
    assert member.name == "Jan Novák"
    assert member.role == "Předseda"
    session.close()


def test_admin_delete_board_member(auth_client, db_engine):
    """POST /sprava/clen/{id}/smazat should delete a board member."""
    from sqlalchemy.orm import Session as SASession
    from app.models.administration import BoardMember

    session = SASession(bind=db_engine)
    member = BoardMember(name="Delete test", role="Člen", group="board")
    session.add(member)
    session.commit()
    mid = member.id
    session.close()

    resp = auth_client.post(f"/sprava/clen/{mid}/smazat", follow_redirects=False)
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(BoardMember).filter(BoardMember.id == mid).first() is None
    session.close()


def test_settings_requires_login(client):
    """GET /nastaveni should redirect to login."""
    resp = client.get("/nastaveni", follow_redirects=False)
    assert resp.status_code == 303


def test_settings_page(auth_client):
    """GET /nastaveni should show settings page."""
    resp = auth_client.get("/nastaveni")
    assert resp.status_code == 200
    assert "Nastavení" in resp.text
