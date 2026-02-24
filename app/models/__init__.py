"""SQLAlchemy ORM models for SVJ Správa."""
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models so Base.metadata knows about them
from app.models.user import User  # noqa: E402, F401
from app.models.owner import Owner, Unit, OwnerUnit, Proxy  # noqa: E402, F401
from app.models.voting import Voting, VotingItem, Ballot, BallotVote  # noqa: E402, F401
from app.models.tax import TaxSession, TaxDocument, TaxDistribution  # noqa: E402, F401
from app.models.sync import SyncSession, SyncRecord  # noqa: E402, F401
from app.models.common import EmailLog, ImportLog, AuditLog, Notification  # noqa: E402, F401
from app.models.administration import SvjInfo, SvjAddress, BoardMember, AutoBackupConfig  # noqa: E402, F401
