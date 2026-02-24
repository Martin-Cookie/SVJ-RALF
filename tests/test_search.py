"""Tests for global search."""


def test_search_requires_login(client, db_session):
    """GET /hledani should redirect when not authenticated."""
    import bcrypt
    from app.models.user import User

    pw = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    user = User(username="testuser", password_hash=pw, role="admin", display_name="Test", is_active=True)
    db_session.add(user)
    db_session.commit()

    resp = client.get("/hledani?q=test", follow_redirects=False)
    assert resp.status_code == 303


def test_search_returns_results(auth_client, db_session):
    """GET /hledani should return matching owners."""
    from app.models.owner import Owner

    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická", is_active=True)
    db_session.add(owner)
    db_session.commit()

    resp = auth_client.get("/hledani?q=Novák")
    assert resp.status_code == 200
    assert "Novák" in resp.text


def test_search_empty_query(auth_client):
    """GET /hledani without query should show prompt."""
    resp = auth_client.get("/hledani?q=")
    assert resp.status_code == 200
    assert "min. 2 znaky" in resp.text
