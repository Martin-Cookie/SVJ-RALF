"""Voting, VotingItem, Ballot, BallotVote models."""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models import Base


class Voting(Base):
    __tablename__ = "votings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="koncept")  # koncept / aktivní / uzavřené / zrušené
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    quorum = Column(Float, default=50.0)
    template_path = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("VotingItem", back_populates="voting", cascade="all, delete-orphan")
    ballots = relationship("Ballot", back_populates="voting", cascade="all, delete-orphan")


class VotingItem(Base):
    __tablename__ = "voting_items"

    id = Column(Integer, primary_key=True, index=True)
    voting_id = Column(Integer, ForeignKey("votings.id"), nullable=False)
    number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False, default="")

    voting = relationship("Voting", back_populates="items")
    ballot_votes = relationship("BallotVote", back_populates="voting_item", cascade="all, delete-orphan")


class Ballot(Base):
    __tablename__ = "ballots"

    id = Column(Integer, primary_key=True, index=True)
    voting_id = Column(Integer, ForeignKey("votings.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    status = Column(String, default="vygenerován")  # vygenerován / odesláno / zpracován / neodevzdán
    pdf_path = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    voting = relationship("Voting", back_populates="ballots")
    owner = relationship("Owner")
    unit = relationship("Unit")
    votes = relationship("BallotVote", back_populates="ballot", cascade="all, delete-orphan")


class BallotVote(Base):
    __tablename__ = "ballot_votes"

    id = Column(Integer, primary_key=True, index=True)
    ballot_id = Column(Integer, ForeignKey("ballots.id"), nullable=False)
    voting_item_id = Column(Integer, ForeignKey("voting_items.id"), nullable=False)
    vote = Column(String, default="")  # PRO / PROTI / Zdržel se

    ballot = relationship("Ballot", back_populates="votes")
    voting_item = relationship("VotingItem", back_populates="ballot_votes")
