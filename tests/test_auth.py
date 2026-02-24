"""Tests for authentication routes."""


def test_login_page_redirects_to_register_when_no_users(client):
    """GET /login should redirect to /registrace when no users exist."""
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 303
    assert "/registrace" in resp.headers["location"]


def test_register_page_shows_form(client):
    """GET /registrace should show registration form when no users."""
    resp = client.get("/registrace")
    assert resp.status_code == 200
    assert "Vytvořte administrátorský účet" in resp.text


def test_register_creates_admin_user(client, db_session):
    """POST /registrace should create first admin user."""
    from app.models.user import User

    resp = client.post(
        "/registrace",
        data={"username": "admin", "password": "secret123", "display_name": "Admin"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"

    user = db_session.query(User).filter_by(username="admin").first()
    assert user is not None
    assert user.role == "admin"
    assert user.display_name == "Admin"


def test_register_rejects_short_password(client):
    """POST /registrace should reject passwords < 6 chars."""
    resp = client.post(
        "/registrace",
        data={"username": "admin", "password": "ab", "display_name": "Admin"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/registrace" in resp.headers["location"]


def test_register_blocked_when_users_exist(auth_client, db_session):
    """GET /registrace should redirect to /login when users already exist."""
    from app.models.user import User

    assert db_session.query(User).count() > 0
    # Use a fresh client that's not logged in
    resp = auth_client.get("/registrace", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_login_success(client, db_session):
    """POST /login with valid credentials should redirect to dashboard."""
    import bcrypt
    from app.models.user import User

    pw = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    user = User(username="testuser", password_hash=pw, role="admin", display_name="Test", is_active=True)
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/login",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_login_failure(client, db_session):
    """POST /login with wrong password should redirect back to /login."""
    import bcrypt
    from app.models.user import User

    pw = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    user = User(username="testuser", password_hash=pw, role="admin", display_name="Test", is_active=True)
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/login",
        data={"username": "testuser", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_logout_clears_session(auth_client):
    """GET /logout should clear session and redirect to /login."""
    resp = auth_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_dashboard_requires_login(client, db_session):
    """GET / without auth should redirect to /login."""
    import bcrypt
    from app.models.user import User

    # Need at least one user so /login doesn't redirect to /registrace
    pw = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    user = User(username="testuser", password_hash=pw, role="admin", display_name="Test", is_active=True)
    db_session.add(user)
    db_session.commit()

    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_dashboard_loads_when_authenticated(auth_client):
    """GET / with auth should return 200 with dashboard."""
    resp = auth_client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
