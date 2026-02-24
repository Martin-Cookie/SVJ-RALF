"""SyncSession, SyncRecord models."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models import Base


class SyncSession(Base):
    __tablename__ = "sync_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="")
    source_format = Column(String, default="")  # sousede.cz / interní
    created_at = Column(DateTime, default=datetime.utcnow)

    records = relationship("SyncRecord", back_populates="session", cascade="all, delete-orphan")


class SyncRecord(Base):
    __tablename__ = "sync_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sync_sessions.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    status = Column(String, default="")  # shoda / částečná / přeházená / rozdílní / rozdílné_podíly / chybí
    db_owner_name = Column(String, default="")
    csv_owner_name = Column(String, default="")
    db_share = Column(String, default="")
    csv_share = Column(String, default="")
    csv_data = Column(Text, default="")  # JSON with full CSV row data
    is_resolved = Column(Integer, default=0)

    session = relationship("SyncSession", back_populates="records")
    unit = relationship("Unit")
