"""Tests for voting processing module — ballot processing, results, import."""


def test_ballot_detail(auth_client, db_engine):
    """GET /hlasovani/{id}/listek/{ballot_id} should show ballot with vote form."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    session.add(VotingItem(voting_id=v.id, number=1, text="Bod 1"))
    ballot = Ballot(voting_id=v.id, owner_id=owner.id, unit_id=unit.id, status="vygenerován")
    session.add(ballot)
    session.commit()
    vid = v.id
    bid = ballot.id
    session.close()

    resp = auth_client.get(f"/hlasovani/{vid}/listek/{bid}")
    assert resp.status_code == 200
    assert "Bod 1" in resp.text
    assert "Jan" in resp.text


def test_process_single_ballot(auth_client, db_engine):
    """POST /hlasovani/{id}/zpracovat/{ballot_id} should record votes."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot, BallotVote
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    item1 = VotingItem(voting_id=v.id, number=1, text="Bod 1")
    item2 = VotingItem(voting_id=v.id, number=2, text="Bod 2")
    session.add_all([item1, item2])
    session.flush()
    ballot = Ballot(voting_id=v.id, owner_id=owner.id, unit_id=unit.id, status="vygenerován")
    session.add(ballot)
    session.commit()
    vid = v.id
    bid = ballot.id
    item1_id = item1.id
    item2_id = item2.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/zpracovat/{bid}",
        data={f"vote_{item1_id}": "PRO", f"vote_{item2_id}": "PROTI"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    votes = session.query(BallotVote).filter(BallotVote.ballot_id == bid).all()
    assert len(votes) == 2
    vote_map = {v.voting_item_id: v.vote for v in votes}
    assert vote_map[item1_id] == "PRO"
    assert vote_map[item2_id] == "PROTI"

    ballot = session.query(Ballot).filter(Ballot.id == bid).first()
    assert ballot.status == "zpracován"
    session.close()


def test_processing_page(auth_client, db_engine):
    """GET /hlasovani/{id}/zpracovani should show processing interface."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    session.add(VotingItem(voting_id=v.id, number=1, text="Bod 1"))
    session.add(Ballot(voting_id=v.id, owner_id=owner.id, unit_id=unit.id, status="vygenerován"))
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.get(f"/hlasovani/{vid}/zpracovani")
    assert resp.status_code == 200
    assert "Zpracování" in resp.text


def test_unsubmitted_ballots(auth_client, db_engine):
    """GET /hlasovani/{id}/neodevzdane should list unprocessed ballots."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, Ballot
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner1 = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    owner2 = Owner(first_name="Eva", last_name="Malá", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner1, owner2, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    session.add(Ballot(voting_id=v.id, owner_id=owner1.id, unit_id=unit.id, status="zpracován"))
    session.add(Ballot(voting_id=v.id, owner_id=owner2.id, unit_id=unit.id, status="vygenerován"))
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.get(f"/hlasovani/{vid}/neodevzdane")
    assert resp.status_code == 200
    assert "Eva" in resp.text


def test_voting_results_with_quorum(auth_client, db_engine):
    """GET /hlasovani/{id} should show results with quorum info."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot, BallotVote
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    item = VotingItem(voting_id=v.id, number=1, text="Bod 1")
    session.add(item)
    session.flush()
    ballot = Ballot(voting_id=v.id, owner_id=owner.id, unit_id=unit.id, status="zpracován")
    session.add(ballot)
    session.flush()
    session.add(BallotVote(ballot_id=ballot.id, voting_item_id=item.id, vote="PRO"))
    session.commit()
    vid = v.id
    session.close()

    resp = auth_client.get(f"/hlasovani/{vid}")
    assert resp.status_code == 200
    assert "PRO" in resp.text
    assert "100" in resp.text  # 100% PRO


def test_bulk_processing(auth_client, db_engine):
    """POST /hlasovani/{id}/zpracovat-hromadne should process multiple ballots."""
    from sqlalchemy.orm import Session as SASession
    from app.models.voting import Voting, VotingItem, Ballot, BallotVote
    from app.models.owner import Owner, Unit

    session = SASession(bind=db_engine)
    owner1 = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    owner2 = Owner(first_name="Eva", last_name="Malá", owner_type="fyzická")
    unit = Unit(unit_number=101, building="A", area=50.0)
    session.add_all([owner1, owner2, unit])
    session.flush()
    v = Voting(name="Test", status="aktivní", quorum=50.0)
    session.add(v)
    session.flush()
    item = VotingItem(voting_id=v.id, number=1, text="Bod 1")
    session.add(item)
    session.flush()
    b1 = Ballot(voting_id=v.id, owner_id=owner1.id, unit_id=unit.id, status="vygenerován")
    b2 = Ballot(voting_id=v.id, owner_id=owner2.id, unit_id=unit.id, status="vygenerován")
    session.add_all([b1, b2])
    session.commit()
    vid = v.id
    b1_id = b1.id
    b2_id = b2.id
    item_id = item.id
    session.close()

    resp = auth_client.post(
        f"/hlasovani/{vid}/zpracovat-hromadne",
        data={
            "ballot_ids": [str(b1_id), str(b2_id)],
            f"vote_{item_id}": "PRO",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    votes = session.query(BallotVote).all()
    assert len(votes) == 2
    for vote in votes:
        assert vote.vote == "PRO"
    b1_check = session.query(Ballot).filter(Ballot.id == b1_id).first()
    b2_check = session.query(Ballot).filter(Ballot.id == b2_id).first()
    assert b1_check.status == "zpracován"
    assert b2_check.status == "zpracován"
    session.close()
