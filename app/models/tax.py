"""TaxSession, TaxDocument, TaxDistribution models."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models import Base


class TaxSession(Base):
    __tablename__ = "tax_sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("TaxDocument", back_populates="session", cascade="all, delete-orphan")


class TaxDocument(Base):
    __tablename__ = "tax_documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("tax_sessions.id"), nullable=False)
    filename = Column(String, nullable=False, default="")
    file_path = Column(String, default="")
    extracted_name = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TaxSession", back_populates="documents")
    distributions = relationship("TaxDistribution", back_populates="document", cascade="all, delete-orphan")


class TaxDistribution(Base):
    __tablename__ = "tax_distributions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("tax_documents.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    matched_name = Column(String, default="")
    match_score = Column(Float, default=0.0)
    is_confirmed = Column(Integer, default=0)  # 0 = nepotvrzeno, 1 = potvrzeno
    email_sent = Column(Integer, default=0)

    document = relationship("TaxDocument", back_populates="distributions")
    owner = relationship("Owner")
