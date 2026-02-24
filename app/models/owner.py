"""Owner, Unit, OwnerUnit, Proxy models."""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Integer, String, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from app.models import Base


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False, default="")
    last_name = Column(String, nullable=False, default="")
    title_before = Column(String, default="")
    title_after = Column(String, default="")
    birth_number = Column(String, default="")  # RČ
    ico = Column(String, default="")  # IČ
    owner_type = Column(String, default="fyzická")  # fyzická / právnická
    email = Column(String, default="")
    phone = Column(String, default="")
    perm_street = Column(String, default="")
    perm_city = Column(String, default="")
    perm_zip = Column(String, default="")
    corr_street = Column(String, default="")
    corr_city = Column(String, default="")
    corr_zip = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_units = relationship("OwnerUnit", back_populates="owner", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        parts = []
        if self.title_before:
            parts.append(self.title_before)
        parts.append(f"{self.last_name} {self.first_name}".strip())
        if self.title_after:
            parts.append(self.title_after)
        return " ".join(parts)


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_number = Column(Integer, nullable=False, index=True)
    building = Column(String, default="")
    section = Column(String, default="")
    space_type = Column(String, default="")
    address = Column(String, default="")
    land_registry_number = Column(String, default="")  # LV
    room_count = Column(Integer, default=0)
    area = Column(Float, default=0.0)
    share_scd = Column(Integer, default=0)  # podíl SČD
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_units = relationship("OwnerUnit", back_populates="unit", cascade="all, delete-orphan")


class OwnerUnit(Base):
    __tablename__ = "owner_units"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    ownership_type = Column(String, default="Neuvedeno")  # SJM, VL, SJVL, Výhradní, Podílové, Neuvedeno
    ownership_share = Column(String, default="")
    voting_weight = Column(Float, default=0.0)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)  # NULL = aktuálně platný

    owner = relationship("Owner", back_populates="owner_units")
    unit = relationship("Unit", back_populates="owner_units")


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    voting_id = Column(Integer, ForeignKey("votings.id"), nullable=False)
    grantor_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    grantee_id = Column(Integer, ForeignKey("owners.id"), nullable=False)

    voting = relationship("Voting", backref="proxies")
    grantor = relationship("Owner", foreign_keys=[grantor_id])
    grantee = relationship("Owner", foreign_keys=[grantee_id])
