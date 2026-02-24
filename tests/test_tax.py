"""Tests for tax distribution module — Blok 6."""


def test_tax_list_requires_login(client):
    """GET /dane should redirect to login for unauthenticated users."""
    resp = client.get("/dane", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers.get("location", "")


def test_tax_list_empty(auth_client):
    """GET /dane should show empty state when no tax sessions exist."""
    resp = auth_client.get("/dane")
    assert resp.status_code == 200
    assert "Daně" in resp.text or "Rozúčtování" in resp.text


def test_tax_create_page(auth_client):
    """GET /dane/nova should show creation form."""
    resp = auth_client.get("/dane/nova")
    assert resp.status_code == 200
    assert "form" in resp.text.lower()


def test_tax_create(auth_client):
    """POST /dane/nova should create a new tax session."""
    resp = auth_client.post(
        "/dane/nova",
        data={"name": "Rozúčtování 2026"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/dane/" in resp.headers.get("location", "")


def test_tax_detail(auth_client, db_engine):
    """GET /dane/{id} should show tax session detail."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession

    session = SASession(bind=db_engine)
    ts = TaxSession(name="Test rozúčtování")
    session.add(ts)
    session.commit()
    ts_id = ts.id
    session.close()

    resp = auth_client.get(f"/dane/{ts_id}")
    assert resp.status_code == 200
    assert "Test rozúčtování" in resp.text


def test_tax_detail_not_found(auth_client):
    """GET /dane/9999 should return 404."""
    resp = auth_client.get("/dane/9999")
    assert resp.status_code == 404


def test_tax_upload_pdf(auth_client, db_engine):
    """POST /dane/{id}/upload should accept PDF files."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession

    session = SASession(bind=db_engine)
    ts = TaxSession(name="Upload test")
    session.add(ts)
    session.commit()
    ts_id = ts.id
    session.close()

    # Create a minimal fake PDF
    pdf_content = b"%PDF-1.4\nfake content"
    resp = auth_client.post(
        f"/dane/{ts_id}/upload",
        files=[("files", ("test.pdf", pdf_content, "application/pdf"))],
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_tax_matching_page(auth_client, db_engine):
    """GET /dane/{id}/parovani should show matching interface."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession, TaxDocument, TaxDistribution
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    session.add(owner)
    session.flush()
    ts = TaxSession(name="Matching test")
    session.add(ts)
    session.flush()
    doc = TaxDocument(session_id=ts.id, filename="test.pdf", extracted_name="Novak Jan")
    session.add(doc)
    session.flush()
    dist = TaxDistribution(document_id=doc.id, owner_id=owner.id, matched_name="Jan Novák", match_score=0.85)
    session.add(dist)
    session.commit()
    ts_id = ts.id
    session.close()

    resp = auth_client.get(f"/dane/{ts_id}/parovani")
    assert resp.status_code == 200
    assert "Novak Jan" in resp.text or "Novák" in resp.text


def test_tax_confirm_match(auth_client, db_engine):
    """POST /dane/{id}/potvrdit/{dist_id} should confirm a match."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession, TaxDocument, TaxDistribution
    from app.models.owner import Owner

    session = SASession(bind=db_engine)
    owner = Owner(first_name="Jan", last_name="Novák", owner_type="fyzická")
    session.add(owner)
    session.flush()
    ts = TaxSession(name="Confirm test")
    session.add(ts)
    session.flush()
    doc = TaxDocument(session_id=ts.id, filename="test.pdf", extracted_name="Novak Jan")
    session.add(doc)
    session.flush()
    dist = TaxDistribution(document_id=doc.id, owner_id=owner.id, matched_name="Jan Novák", match_score=0.85)
    session.add(dist)
    session.commit()
    ts_id = ts.id
    dist_id = dist.id
    session.close()

    resp = auth_client.post(
        f"/dane/{ts_id}/potvrdit/{dist_id}",
        follow_redirects=False,
    )
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    dist_check = session.query(TaxDistribution).filter(TaxDistribution.id == dist_id).first()
    assert dist_check.is_confirmed == 1
    session.close()


def test_tax_delete(auth_client, db_engine):
    """POST /dane/{id}/smazat should delete a tax session."""
    from sqlalchemy.orm import Session as SASession
    from app.models.tax import TaxSession

    session = SASession(bind=db_engine)
    ts = TaxSession(name="Delete test")
    session.add(ts)
    session.commit()
    ts_id = ts.id
    session.close()

    resp = auth_client.post(f"/dane/{ts_id}/smazat", follow_redirects=False)
    assert resp.status_code == 303

    session = SASession(bind=db_engine)
    assert session.query(TaxSession).filter(TaxSession.id == ts_id).first() is None
    session.close()
