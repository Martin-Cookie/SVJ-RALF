"""Shared test fixtures for SVJ Správa."""
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test env before importing app modules
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["GENERATED_DIR"] = tempfile.mkdtemp()


@pytest.fixture
def db_engine():
    """Create a fresh in-memory SQLite engine for each test.

    Uses StaticPool so all connections share the same in-memory database.
    """
    from app.models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a DB session bound to the test engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    """Create a FastAPI test client with overridden DB."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session as SASession

    from app.database import get_db
    from app.main import app

    def override_get_db():
        session = SASession(bind=db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client, db_engine):
    """Client with an authenticated admin user."""
    from sqlalchemy.orm import Session as SASession

    from app.models.user import User

    import bcrypt

    session = SASession(bind=db_engine)
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    user = User(
        username="admin",
        password_hash=pw_hash,
        role="admin",
        display_name="Test Admin",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.close()

    # Login
    client.post("/login", data={"username": "admin", "password": "testpass123"})
    return client


@pytest.fixture
def editor_client(client, db_engine):
    """Client with an authenticated editor user."""
    from sqlalchemy.orm import Session as SASession

    from app.models.user import User

    import bcrypt

    session = SASession(bind=db_engine)
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    user = User(
        username="editor",
        password_hash=pw_hash,
        role="editor",
        display_name="Test Editor",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.close()

    # Login
    client.post("/login", data={"username": "editor", "password": "testpass123"})
    return client


@pytest.fixture
def reader_client(client, db_engine):
    """Client with an authenticated reader user."""
    from sqlalchemy.orm import Session as SASession

    from app.models.user import User

    import bcrypt

    session = SASession(bind=db_engine)
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    user = User(
        username="reader",
        password_hash=pw_hash,
        role="reader",
        display_name="Test Reader",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.close()

    # Login
    client.post("/login", data={"username": "reader", "password": "testpass123"})
    return client
