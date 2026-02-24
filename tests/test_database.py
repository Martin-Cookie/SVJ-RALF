"""Tests for database setup and models."""


def test_engine_creates(db_engine):
    """SQLAlchemy engine should be created."""
    assert db_engine is not None


def test_all_tables_created(db_engine):
    """All model tables should be created in the database."""
    from sqlalchemy import inspect

    inspector = inspect(db_engine)
    table_names = inspector.get_table_names()

    expected_tables = [
        "users",
        "owners",
        "units",
        "owner_units",
        "proxies",
        "votings",
        "voting_items",
        "ballots",
        "ballot_votes",
        "tax_sessions",
        "tax_documents",
        "tax_distributions",
        "sync_sessions",
        "sync_records",
        "svj_info",
        "svj_addresses",
        "board_members",
        "email_logs",
        "import_logs",
        "audit_logs",
        "notifications",
        "auto_backup_config",
    ]

    for table in expected_tables:
        assert table in table_names, f"Table '{table}' missing from database"


def test_create_user(db_session):
    """Should be able to create a User record."""
    from app.models.user import User

    user = User(
        username="testuser",
        password_hash="fakehash",
        role="admin",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    result = db_session.query(User).filter_by(username="testuser").first()
    assert result is not None
    assert result.display_name == "Test User"
    assert result.role == "admin"
    assert result.is_active is True


def test_create_owner(db_session):
    """Should be able to create an Owner record."""
    from app.models.owner import Owner

    owner = Owner(
        first_name="Jan",
        last_name="Novák",
        owner_type="fyzická",
        is_active=True,
    )
    db_session.add(owner)
    db_session.commit()

    result = db_session.query(Owner).filter_by(last_name="Novák").first()
    assert result is not None
    assert result.first_name == "Jan"


def test_create_unit(db_session):
    """Should be able to create a Unit record."""
    from app.models.owner import Unit

    unit = Unit(unit_number=101, building="A", section="I", space_type="byt")
    db_session.add(unit)
    db_session.commit()

    result = db_session.query(Unit).filter_by(unit_number=101).first()
    assert result is not None
    assert result.building == "A"


def test_owner_unit_relationship(db_session):
    """OwnerUnit should link Owner and Unit."""
    from app.models.owner import Owner, OwnerUnit, Unit

    owner = Owner(first_name="Jana", last_name="Nováková", owner_type="fyzická")
    unit = Unit(unit_number=201, building="B")
    db_session.add_all([owner, unit])
    db_session.flush()

    ou = OwnerUnit(
        owner_id=owner.id,
        unit_id=unit.id,
        ownership_type="VL",
        ownership_share="1/1",
    )
    db_session.add(ou)
    db_session.commit()

    result = db_session.query(OwnerUnit).first()
    assert result.owner_id == owner.id
    assert result.unit_id == unit.id


def test_create_voting(db_session):
    """Should be able to create a Voting record."""
    from app.models.voting import Voting

    voting = Voting(name="Test hlasování", status="koncept", quorum=50.0)
    db_session.add(voting)
    db_session.commit()

    result = db_session.query(Voting).first()
    assert result.name == "Test hlasování"
    assert result.status == "koncept"
