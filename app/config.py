"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_PATH: str = "data/svj.db"
    UPLOAD_DIR: str = "data/uploads"
    GENERATED_DIR: str = "data/generated"
    BACKUP_DIR: str = "data/backups"
    SECRET_KEY: str = "change-me-in-production"
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "svj@example.com"
    SMTP_FROM_NAME: str = "SVJ"
    LIBREOFFICE_PATH: str = "/Applications/LibreOffice.app/Contents/MacOS/soffice"


settings = Settings()
