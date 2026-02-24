"""Tests for Enhanced Voting Import — Iterace 15, Block G.

Covers: column mapping step, configurable start row, import mode, SJM matching.
"""
import io
import openpyxl


def _create_voting_with_items(db_engine):
    """Helper to create a voting with items, ballots."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    voting = Voting(name="Test Enhanced Import", status="aktivní", quorum=50)
    session.add(voting)
    session.flush()

    item1 = VotingItem(voting_id=voting.id, number=1, text="Oprava střechy")
    item2 = VotingItem(voting_id=voting.id, number=2, text="Fond oprav")
    session.add_all([item1, item2])

    # Create two owners: one regular, one SJM pair
    owner1 = Owner(first_name="Jan", last_name="Novák", owner_type="physical", name_normalized="novák jan")
    owner2 = Owner(first_name="Jana", last_name="Nováková", owner_type="physical", name_normalized="nováková jana")
    unit1 = Unit(unit_number=101, space_type="Byt")
    unit2 = Unit(unit_number=102, space_type="Byt")
    session.add_all([owner1, owner2, unit1, unit2])
    session.flush()

    # Both owners on unit1 (SJM pair)
    ou1 = OwnerUnit(owner_id=owner1.id, unit_id=unit1.id)
    ou2 = OwnerUnit(owner_id=owner2.id, unit_id=unit1.id)
    ou3 = OwnerUnit(owner_id=owner1.id, unit_id=unit2.id)
    session.add_all([ou1, ou2, ou3])

    ballot1 = Ballot(voting_id=voting.id, owner_id=owner1.id, unit_id=unit1.id, status="vygenerován")
    ballot2 = Ballot(voting_id=voting.id, owner_id=owner2.id, unit_id=unit1.id, status="vygenerován")
    ballot3 = Ballot(voting_id=voting.id, owner_id=owner1.id, unit_id=unit2.id, status="vygenerován")
    session.add_all([ballot1, ballot2, ballot3])
    session.commit()

    result = {
        "voting_id": voting.id,
        "item1_id": item1.id,
        "item2_id": item2.id,
        "owner1_id": owner1.id,
        "owner2_id": owner2.id,
        "unit1_id": unit1.id,
        "unit2_id": unit2.id,
        "ballot1_id": ballot1.id,
        "ballot2_id": ballot2.id,
        "ballot3_id": ballot3.id,
    }
    session.close()
    return result


def _create_excel_with_headers(headers, rows):
    """Create Excel with custom headers and rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def test_upload_returns_column_mapping(auth_client, db_engine):
    """Upload step should return column mapping UI with detected headers."""
    data = _create_voting_with_items(db_engine)
    excel = _create_excel_with_headers(
        ["Jméno", "Číslo bytu", "Oprava střechy", "Fond oprav"],
        [["Novák Jan", "101", "PRO", "PROTI"]],
    )
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should show column mapping UI with detected headers
    assert "mapping" in resp.text.lower() or "mapování" in resp.text.lower() or "sloupce" in resp.text.lower()


def test_column_mapping_submit_returns_preview(auth_client, db_engine):
    """After column mapping, should show import preview."""
    data = _create_voting_with_items(db_engine)
    excel = _create_excel_with_headers(
        ["Jméno", "Číslo bytu", "Oprava střechy", "Fond oprav"],
        [["Novák Jan", "101", "PRO", "PROTI"]],
    )
    # Upload first
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    # Submit column mapping
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/mapovani",
        data={
            "owner_col": "0",
            "unit_col": "1",
            "start_row": "2",
            "import_mode": "doplnit",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should show preview with matched/unmatched stats
    assert "náhled" in resp.text.lower() or "preview" in resp.text.lower() or "potvrdit" in resp.text.lower()


def test_configurable_start_row(auth_client, db_engine):
    """Import should skip rows before start_row."""
    data = _create_voting_with_items(db_engine)
    # Excel with 2 header rows (start data at row 3)
    excel = _create_excel_with_headers(
        ["Report: Hlasování"],
        [
            ["Jméno", "Číslo bytu", "Oprava střechy", "Fond oprav"],
            ["Novák Jan", "101", "PRO", "PROTI"],
        ],
    )
    # Upload
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    # Map columns with start_row=3
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/mapovani",
        data={
            "owner_col": "0",
            "unit_col": "1",
            "start_row": "3",
            "import_mode": "doplnit",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should find 1 data row, not 2
    assert "1" in resp.text  # 1 row matched


def test_import_mode_replace(auth_client, db_engine):
    """Import mode 'přepsat' should clear existing votes before import."""
    data = _create_voting_with_items(db_engine)
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import BallotVote

    # Pre-create an existing vote
    session = SASession(bind=db_engine)
    existing = BallotVote(ballot_id=data["ballot1_id"], voting_item_id=data["item1_id"], vote="PROTI")
    session.add(existing)
    session.commit()
    session.close()

    excel = _create_excel_with_headers(
        ["Jméno", "Číslo bytu", "Oprava střechy", "Fond oprav"],
        [["Novák Jan", "101", "PRO", "PROTI"]],
    )
    # Upload
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    # Map with mode=přepsat
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/mapovani",
        data={
            "owner_col": "0",
            "unit_col": "1",
            "start_row": "2",
            "import_mode": "prepsat",
        },
    )
    # Confirm
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/potvrdit",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify: vote should be PRO now (replaced), not PROTI
    session = SASession(bind=db_engine)
    vote = session.query(BallotVote).filter(
        BallotVote.ballot_id == data["ballot1_id"],
        BallotVote.voting_item_id == data["item1_id"],
    ).first()
    assert vote is not None
    assert vote.vote == "PRO"
    session.close()


def test_sjm_matching(auth_client, db_engine):
    """Import should match SJM co-owners: one row → multiple ballots on same unit."""
    data = _create_voting_with_items(db_engine)
    excel = _create_excel_with_headers(
        ["Jméno", "Číslo bytu", "Oprava střechy", "Fond oprav"],
        [["Novák Jan", "101", "PRO", "PRO"]],
    )
    # Upload
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    # Map
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/mapovani",
        data={
            "owner_col": "0",
            "unit_col": "1",
            "start_row": "2",
            "import_mode": "doplnit",
        },
    )
    # Confirm
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/potvrdit",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Verify: both ballot1 (owner1+unit1) and ballot2 (owner2+unit1) should have votes
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import BallotVote, Ballot
    session = SASession(bind=db_engine)
    b1_votes = session.query(BallotVote).filter(BallotVote.ballot_id == data["ballot1_id"]).count()
    b2_votes = session.query(BallotVote).filter(BallotVote.ballot_id == data["ballot2_id"]).count()
    assert b1_votes == 2  # 2 items
    assert b2_votes == 2  # SJM co-owner gets same votes
    session.close()
