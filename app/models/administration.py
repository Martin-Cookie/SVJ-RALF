"""Administration models: SvjInfo, SvjAddress, BoardMember, AutoBackupConfig."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.models import Base


class SvjInfo(Base):
    __tablename__ = "svj_info"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    building_type = Column(String, default="")
    total_shares = Column(Integer, default=0)


class SvjAddress(Base):
    __tablename__ = "svj_addresses"

    id = Column(Integer, primary_key=True, index=True)
    street = Column(String, default="")
    city = Column(String, default="")
    zip_code = Column(String, default="")


class BoardMember(Base):
    __tablename__ = "board_members"

    id = Column(Integer, primary_key=True, index=True)
    group = Column(String, default="board")  # board / control
    name = Column(String, nullable=False, default="")
    role = Column(String, default="")  # Předseda / Místopředseda / Člen
    email = Column(String, default="")
    phone = Column(String, default="")


class AutoBackupConfig(Base):
    __tablename__ = "auto_backup_config"

    id = Column(Integer, primary_key=True, index=True)
    frequency = Column(String, default="daily")  # daily / weekly
    time = Column(String, default="02:00")  # HH:MM
    max_backups = Column(Integer, default=7)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    is_enabled = Column(Boolean, default=False)
