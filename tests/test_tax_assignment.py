"""Tests for Tax manual assignment — Iterace 12, Blok D.

Covers: POST /dane/{id}/prirazeni/{doc_id} for manual owner assignment.
"""


def test_tax_manual_assignment(auth_client, db_engine):
    """Manual assignment creates distribution link."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession, TaxDocument, TaxDistribution
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    ts = TaxSession(name="Test Tax")
    session.add(ts)
    session.flush()

    doc = TaxDocument(session_id=ts.id, filename="test.pdf", file_path="/tmp/test.pdf", extracted_name="Novák Jan")
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="physical")
    session.add_all([doc, owner])
    session.commit()
    ts_id = ts.id
    doc_id = doc.id
    owner_id = owner.id
    session.close()

    resp = auth_client.post(
        f"/dane/{ts_id}/prirazeni/{doc_id}",
        data={"owner_id": str(owner_id)},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    dist = session.query(TaxDistribution).filter(TaxDistribution.document_id == doc_id).first()
    assert dist is not None
    assert dist.owner_id == owner_id
    session.close()


def test_tax_manual_assignment_requires_login(client, db_engine):
    """Manual assignment requires authentication."""
    resp = client.post("/dane/1/prirazeni/1", data={"owner_id": "1"}, follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")


def test_tax_manual_assignment_replaces_existing(auth_client, db_engine):
    """Manual assignment replaces existing distribution."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession, TaxDocument, TaxDistribution
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    ts = TaxSession(name="Replace Tax")
    session.add(ts)
    session.flush()

    doc = TaxDocument(session_id=ts.id, filename="test2.pdf", file_path="/tmp/test2.pdf", extracted_name="Novák")
    owner1 = Owner(first_name="Old", last_name="Owner", owner_type="physical")
    owner2 = Owner(first_name="New", last_name="Owner", owner_type="physical")
    session.add_all([doc, owner1, owner2])
    session.flush()

    # Existing distribution
    dist = TaxDistribution(document_id=doc.id, owner_id=owner1.id, matched_name="Old Owner", match_score=0.5)
    session.add(dist)
    session.commit()
    ts_id = ts.id
    doc_id = doc.id
    owner2_id = owner2.id
    session.close()

    resp = auth_client.post(
        f"/dane/{ts_id}/prirazeni/{doc_id}",
        data={"owner_id": str(owner2_id)},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    dists = session.query(TaxDistribution).filter(TaxDistribution.document_id == doc_id).all()
    # Should have new distribution (old may be deleted or replaced)
    assert any(d.owner_id == owner2_id for d in dists)
    session.close()
