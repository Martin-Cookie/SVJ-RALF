"""Common models: EmailLog, ImportLog, AuditLog, Notification."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Text

from app.models import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String, nullable=False, default="")
    subject = Column(String, default="")
    status = Column(String, default="")  # sent / failed
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ImportLog(Base):
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, default="")  # excel / csv / manual
    filename = Column(String, default="")
    records_count = Column(Integer, default=0)
    status = Column(String, default="")  # success / partial / failed
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False, default="")  # create / update / delete
    model_name = Column(String, default="")
    record_id = Column(Integer, nullable=True)
    field_name = Column(String, default="")
    old_value = Column(Text, default="")
    new_value = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String, default="")  # voting_created / voting_status / import_done / sync_done / backup_done
    message = Column(String, default="")
    link = Column(String, default="")  # URL
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
