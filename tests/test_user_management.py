"""Tests for user management — Blok A (iter 10)."""
import bcrypt


# --- User list page ---


def test_user_list_requires_admin(editor_client):
    """GET /sprava/uzivatele should return 403 for non-admin users."""
    resp = editor_client.get("/sprava/uzivatele", follow_redirects=False)
    assert resp.status_code == 403


def test_user_list_requires_login(client):
    """GET /sprava/uzivatele should redirect to login for unauthenticated."""
    resp = client.get("/sprava/uzivatele", follow_redirects=False)
    assert resp.status_code == 303


def test_user_list_shows_users(auth_client):
    """GET /sprava/uzivatele should show user list for admin."""
    resp = auth_client.get("/sprava/uzivatele")
    assert resp.status_code == 200
    assert "Správa uživatelů" in resp.text
    assert "admin" in resp.text


# --- Create user ---


def test_create_user(auth_client, db_engine):
    """POST /sprava/uzivatele/novy should create a new user."""
    resp = auth_client.post(
        "/sprava/uzivatele/novy",
        data={
            "username": "novyeditor",
            "password": "heslo123",
            "display_name": "Nový Editor",
            "role": "editor",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    session = SASession(bind=db_engine)
    user = session.query(User).filter(User.username == "novyeditor").first()
    assert user is not None
    assert user.role == "editor"
    assert user.display_name == "Nový Editor"
    assert bcrypt.checkpw(b"heslo123", user.password_hash.encode())
    session.close()


def test_create_user_duplicate_username(auth_client):
    """POST /sprava/uzivatele/novy with existing username should fail."""
    resp = auth_client.post(
        "/sprava/uzivatele/novy",
        data={
            "username": "admin",
            "password": "heslo123",
            "display_name": "Duplicate",
            "role": "reader",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Follow redirect and check flash error
    resp2 = auth_client.get("/sprava/uzivatele")
    assert "již existuje" in resp2.text or resp.status_code == 303


def test_create_user_short_password(auth_client):
    """POST /sprava/uzivatele/novy with short password should fail."""
    resp = auth_client.post(
        "/sprava/uzivatele/novy",
        data={
            "username": "shortpw",
            "password": "ab",
            "display_name": "Short PW",
            "role": "reader",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_create_user_requires_admin(editor_client):
    """POST /sprava/uzivatele/novy should fail for non-admin."""
    resp = editor_client.post(
        "/sprava/uzivatele/novy",
        data={
            "username": "hacker",
            "password": "heslo123",
            "display_name": "Hacker",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 403


# --- Change role ---


def test_change_user_role(auth_client, db_engine):
    """POST /sprava/uzivatele/{id}/role should change user role."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    # Create a reader user
    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"pass123456", bcrypt.gensalt()).decode()
    u = User(username="roletest", password_hash=pw, role="reader", display_name="Role Test")
    session.add(u)
    session.commit()
    uid = u.id
    session.close()

    resp = auth_client.post(
        f"/sprava/uzivatele/{uid}/role",
        data={"role": "editor"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    u = session.query(User).filter(User.id == uid).first()
    assert u.role == "editor"
    session.close()


# --- Reset password ---


def test_reset_password(auth_client, db_engine):
    """POST /sprava/uzivatele/{id}/heslo should reset user password."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"oldpassword", bcrypt.gensalt()).decode()
    u = User(username="pwreset", password_hash=pw, role="reader", display_name="PW Reset")
    session.add(u)
    session.commit()
    uid = u.id
    session.close()

    resp = auth_client.post(
        f"/sprava/uzivatele/{uid}/heslo",
        data={"password": "newpassword123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    u = session.query(User).filter(User.id == uid).first()
    assert bcrypt.checkpw(b"newpassword123", u.password_hash.encode())
    session.close()


# --- Activate/Deactivate ---


def test_deactivate_user(auth_client, db_engine):
    """POST /sprava/uzivatele/{id}/stav should deactivate user."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    session = SASession(bind=db_engine)
    pw = bcrypt.hashpw(b"pass123456", bcrypt.gensalt()).decode()
    u = User(username="deacttest", password_hash=pw, role="reader", display_name="Deact Test")
    session.add(u)
    session.commit()
    uid = u.id
    session.close()

    resp = auth_client.post(
        f"/sprava/uzivatele/{uid}/stav",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    u = session.query(User).filter(User.id == uid).first()
    assert u.is_active is False
    session.close()


def test_cannot_deactivate_self(auth_client, db_engine):
    """Admin should not be able to deactivate themselves."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    session = SASession(bind=db_engine)
    admin = session.query(User).filter(User.username == "admin").first()
    admin_id = admin.id
    session.close()

    resp = auth_client.post(
        f"/sprava/uzivatele/{admin_id}/stav",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Admin should still be active
    session = SASession(bind=db_engine)
    admin = session.query(User).filter(User.id == admin_id).first()
    assert admin.is_active is True
    session.close()


def test_cannot_demote_last_admin(auth_client, db_engine):
    """Cannot change the last admin's role to non-admin."""
    from sqlalchemy.orm import Session as SASession
    from app.models.user import User

    session = SASession(bind=db_engine)
    admin = session.query(User).filter(User.username == "admin").first()
    admin_id = admin.id
    session.close()

    resp = auth_client.post(
        f"/sprava/uzivatele/{admin_id}/role",
        data={"role": "editor"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Admin role should remain unchanged
    session = SASession(bind=db_engine)
    admin = session.query(User).filter(User.id == admin_id).first()
    assert admin.role == "admin"
    session.close()


# --- Role-based access on admin routes ---


def test_admin_page_requires_admin_role(editor_client):
    """Editor should not be able to access /sprava."""
    resp = editor_client.get("/sprava", follow_redirects=False)
    assert resp.status_code == 403


def test_reader_cannot_access_admin(reader_client):
    """Reader should not be able to access /sprava."""
    resp = reader_client.get("/sprava", follow_redirects=False)
    assert resp.status_code == 403
