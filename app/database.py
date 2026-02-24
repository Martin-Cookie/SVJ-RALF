"""SQLAlchemy database engine and session management."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

_db_path = settings.DATABASE_PATH
if _db_path == ":memory:":
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
else:
    os.makedirs(os.path.dirname(_db_path) or ".", exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
