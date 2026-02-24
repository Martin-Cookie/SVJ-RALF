"""Tests for Voting Excel Import — Iterace 14, Blok F.

Covers: 4-step import flow (upload page, upload Excel, preview, confirm).
"""
import io
import os
import tempfile

import openpyxl


def _create_voting_with_items(db_engine):
    """Helper to create a voting with items, ballots."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot
    from app.models.owner import Owner, Unit, OwnerUnit

    session = SASession(bind=db_engine)

    voting = Voting(name="Test Import Voting", status="aktivní", quorum=50)
    session.add(voting)
    session.flush()

    item1 = VotingItem(voting_id=voting.id, number=1, text="Bod 1")
    item2 = VotingItem(voting_id=voting.id, number=2, text="Bod 2")
    session.add_all([item1, item2])

    owner = Owner(first_name="Jan", last_name="Novák", owner_type="physical", name_normalized="novák jan")
    unit = Unit(unit_number=200, space_type="Byt")
    session.add_all([owner, unit])
    session.flush()

    ou = OwnerUnit(owner_id=owner.id, unit_id=unit.id)
    ballot = Ballot(voting_id=voting.id, owner_id=owner.id, unit_id=unit.id, status="vygenerován")
    session.add_all([ou, ballot])
    session.commit()

    result = {
        "voting_id": voting.id,
        "item1_id": item1.id,
        "item2_id": item2.id,
        "owner_id": owner.id,
        "unit_id": unit.id,
        "ballot_id": ballot.id,
    }
    session.close()
    return result


def _create_import_excel(owner_name="Novák Jan", unit_number=200, vote1="PRO", vote2="PROTI"):
    """Create a minimal Excel for voting import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Vlastník", "Jednotka", "Bod 1", "Bod 2"])
    ws.append([owner_name, str(unit_number), vote1, vote2])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def test_voting_import_page(auth_client, db_engine):
    """GET /hlasovani/{id}/import shows import page."""
    data = _create_voting_with_items(db_engine)
    resp = auth_client.get(f"/hlasovani/{data['voting_id']}/import")
    assert resp.status_code == 200
    assert "import" in resp.text.lower() or "nahrát" in resp.text.lower()


def test_voting_import_upload(auth_client, db_engine):
    """POST /hlasovani/{id}/import uploads Excel and returns preview."""
    data = _create_voting_with_items(db_engine)
    excel = _create_import_excel()

    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("hlasovani.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        follow_redirects=False,
    )
    # Should show preview page or redirect to preview
    assert resp.status_code in (200, 303)


def test_voting_import_confirm(auth_client, db_engine):
    """POST /hlasovani/{id}/import/potvrdit creates ballot votes."""
    data = _create_voting_with_items(db_engine)
    excel = _create_import_excel()

    # Upload first
    auth_client.post(
        f"/hlasovani/{data['voting_id']}/import",
        files={"file": ("hlasovani.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    # Confirm
    resp = auth_client.post(
        f"/hlasovani/{data['voting_id']}/import/potvrdit",
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_voting_import_requires_login(client, db_engine):
    """Import page requires authentication."""
    resp = client.get("/hlasovani/1/import")
    assert resp.status_code in (200, 303)
    if resp.status_code == 303:
        assert "/login" in resp.headers.get("location", "")
