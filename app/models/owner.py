"""Owner, Unit, OwnerUnit, Proxy models.

Matches the proven data schema from the original SVJ project.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Index, Integer, String, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from app.models import Base


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)

    # Identity (Excel columns L, M, N)
    first_name = Column(String, nullable=False, default="", index=True)
    last_name = Column(String, nullable=True, default="", index=True)
    title = Column(String, nullable=True, default="")
    name_with_titles = Column(String, nullable=False, default="", index=True)
    name_normalized = Column(String, nullable=False, default="", index=True)
    owner_type = Column(String, nullable=False, default="physical", index=True)  # physical / legal

    # Identification (Excel column O)
    birth_number = Column(String, nullable=True, default="", index=True)  # RČ
    company_id = Column(String, nullable=True, default="", index=True)  # IČ

    # Permanent address (Excel columns P-T)
    perm_street = Column(String, nullable=True, default="")
    perm_district = Column(String, nullable=True, default="")
    perm_city = Column(String, nullable=True, default="", index=True)
    perm_zip = Column(String, nullable=True, default="")
    perm_country = Column(String, nullable=True, default="")

    # Correspondence address (Excel columns U-Y)
    corr_street = Column(String, nullable=True, default="")
    corr_district = Column(String, nullable=True, default="")
    corr_city = Column(String, nullable=True, default="")
    corr_zip = Column(String, nullable=True, default="")
    corr_country = Column(String, nullable=True, default="")

    # Contact (Excel columns Z, AA, AB, AC)
    phone = Column(String, nullable=True, default="", index=True)
    phone_landline = Column(String, nullable=True, default="")
    email = Column(String, nullable=True, default="", index=True)
    email_secondary = Column(String, nullable=True, default="")

    # Metadata (Excel columns AD, AE)
    owner_since = Column(String, nullable=True, default="")
    note = Column(Text, nullable=True, default="")

    data_source = Column(String, default="excel")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_units = relationship("OwnerUnit", back_populates="owner", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        """Name in 'titul příjmení jméno' format."""
        parts = []
        if self.title:
            parts.append(self.title)
        if self.last_name:
            parts.append(self.last_name)
        if self.first_name:
            parts.append(self.first_name)
        return " ".join(parts) if parts else (self.name_with_titles or "")

    @property
    def current_units(self):
        return [ou for ou in self.owner_units if ou.valid_to is None]

    @property
    def historical_units(self):
        return [ou for ou in self.owner_units if ou.valid_to is not None]


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_number = Column(Integer, nullable=False, unique=True, index=True)
    building_number = Column(String, nullable=True, default="", index=True)
    podil_scd = Column(Integer, nullable=True, default=0)  # podíl SČD
    floor_area = Column(Float, nullable=True, default=0.0)
    room_count = Column(String, nullable=True, default="")  # "3+1" etc.
    space_type = Column(String, nullable=True, default="", index=True)
    section = Column(String, nullable=True, default="", index=True)
    orientation_number = Column(Integer, nullable=True)
    address = Column(String, nullable=True, default="")
    lv_number = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner_units = relationship("OwnerUnit", back_populates="unit", cascade="all, delete-orphan")

    @property
    def current_owners(self):
        return [ou for ou in self.owner_units if ou.valid_to is None]

    @property
    def historical_owners(self):
        return [ou for ou in self.owner_units if ou.valid_to is not None]


class OwnerUnit(Base):
    __tablename__ = "owner_units"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    ownership_type = Column(String, nullable=True, default="", index=True)  # SJM, VL, SJVL, etc.
    share = Column(Float, nullable=False, default=1.0)
    votes = Column(Integer, nullable=False, default=0)
    excel_row_number = Column(Integer, nullable=True)
    valid_from = Column(Date, nullable=True, index=True)
    valid_to = Column(Date, nullable=True, index=True)  # NULL = aktuálně platný

    owner = relationship("Owner", back_populates="owner_units")
    unit = relationship("Unit", back_populates="owner_units")

    __table_args__ = (
        Index("ix_owner_unit_composite", "owner_id", "unit_id"),
    )


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    voting_id = Column(Integer, ForeignKey("votings.id"), nullable=False)
    grantor_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    grantee_id = Column(Integer, ForeignKey("owners.id"), nullable=False)

    voting = relationship("Voting", backref="proxies")
    grantor = relationship("Owner", foreign_keys=[grantor_id])
    grantee = relationship("Owner", foreign_keys=[grantee_id])
