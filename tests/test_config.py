"""Tests for app configuration."""
import os


def test_config_loads_from_env():
    """Config should load values from environment variables."""
    from app.config import settings

    assert settings.DATABASE_PATH is not None
    assert settings.SECRET_KEY is not None


def test_config_has_required_fields():
    """Config should have all required fields."""
    from app.config import settings

    assert hasattr(settings, "DATABASE_PATH")
    assert hasattr(settings, "UPLOAD_DIR")
    assert hasattr(settings, "GENERATED_DIR")
    assert hasattr(settings, "SECRET_KEY")
    assert hasattr(settings, "SMTP_HOST")
    assert hasattr(settings, "SMTP_PORT")
