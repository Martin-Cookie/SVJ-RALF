"""Tax distribution (Rozúčtování) routes."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.tax import TaxSession, TaxDocument, TaxDistribution

router = APIRouter()


@router.get("/dane", response_class=HTMLResponse)
def tax_list(request: Request, db: Session = Depends(get_db)):
    """List all tax sessions."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    sessions = db.query(TaxSession).order_by(TaxSession.created_at.desc()).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "tax/list.html",
        {"user": user, "sessions": sessions},
    )


@router.get("/dane/nova", response_class=HTMLResponse)
def tax_create_page(request: Request, db: Session = Depends(get_db)):
    """Show new tax session creation form."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    return request.app.state.templates.TemplateResponse(
        request, "tax/create.html", {"user": user}
    )


@router.post("/dane/nova")
def tax_create(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    """Create a new tax session."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ts = TaxSession(name=name)
    db.add(ts)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Rozúčtování '{name}' vytvořeno."}
    return RedirectResponse(url=f"/dane/{ts.id}", status_code=303)


@router.get("/dane/{session_id}", response_class=HTMLResponse)
def tax_detail(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Show tax session detail with documents."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ts = db.query(TaxSession).filter(TaxSession.id == session_id).first()
    if ts is None:
        return HTMLResponse("Rozúčtování nenalezeno", status_code=404)

    documents = (
        db.query(TaxDocument)
        .filter(TaxDocument.session_id == session_id)
        .order_by(TaxDocument.created_at.desc())
        .all()
    )

    # Count matched/unmatched
    total_docs = len(documents)
    matched_count = 0
    for doc in documents:
        dists = db.query(TaxDistribution).filter(TaxDistribution.document_id == doc.id).all()
        if any(d.is_confirmed == 1 for d in dists):
            matched_count += 1

    return request.app.state.templates.TemplateResponse(
        request,
        "tax/detail.html",
        {
            "user": user,
            "session": ts,
            "documents": documents,
            "total_docs": total_docs,
            "matched_count": matched_count,
        },
    )


@router.get("/dane/{session_id}/pdf/{doc_id}")
def tax_serve_pdf(
    session_id: int,
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Serve a PDF file for inline viewing."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    doc = db.query(TaxDocument).filter(
        TaxDocument.id == doc_id,
        TaxDocument.session_id == session_id,
    ).first()
    if doc is None:
        return HTMLResponse("Dokument nenalezen", status_code=404)

    file_path = doc.file_path
    if not file_path or not os.path.exists(file_path):
        return HTMLResponse("Soubor nenalezen na disku", status_code=404)

    # Path traversal protection
    real_path = os.path.realpath(file_path)
    allowed_dir = os.path.realpath(os.path.join(settings.UPLOAD_DIR, "tax"))
    if not real_path.startswith(allowed_dir + os.sep):
        return HTMLResponse("Neplatná cesta souboru", status_code=403)

    def iterfile():
        with open(real_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={doc.filename}"},
    )


@router.post("/dane/{session_id}/upload")
async def tax_upload_pdf(
    session_id: int,
    request: Request,
    files: list = File(...),
    db: Session = Depends(get_db),
):
    """Upload PDF documents to a tax session."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ts = db.query(TaxSession).filter(TaxSession.id == session_id).first()
    if ts is None:
        return HTMLResponse("Rozúčtování nenalezeno", status_code=404)

    upload_dir = os.path.join(settings.UPLOAD_DIR, "tax", str(session_id))
    os.makedirs(upload_dir, exist_ok=True)

    uploaded = 0
    for f in files:
        if hasattr(f, 'filename') and f.filename:
            file_path = os.path.join(upload_dir, f.filename)
            content = await f.read()
            with open(file_path, "wb") as out:
                out.write(content)

            # Extract name from PDF (best-effort)
            extracted_name = _extract_name_from_pdf(file_path)

            doc = TaxDocument(
                session_id=session_id,
                filename=f.filename,
                file_path=file_path,
                extracted_name=extracted_name,
            )
            db.add(doc)
            db.flush()

            # Auto-match to owners
            _auto_match_document(db, doc)
            uploaded += 1

    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Nahráno {uploaded} souborů."}
    return RedirectResponse(url=f"/dane/{session_id}", status_code=303)


@router.get("/dane/{session_id}/parovani", response_class=HTMLResponse)
def tax_matching_page(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Show matching interface for a tax session."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ts = db.query(TaxSession).filter(TaxSession.id == session_id).first()
    if ts is None:
        return HTMLResponse("Rozúčtování nenalezeno", status_code=404)

    # Get all documents with their distributions
    documents = (
        db.query(TaxDocument)
        .filter(TaxDocument.session_id == session_id)
        .all()
    )

    matches = []
    for doc in documents:
        dists = (
            db.query(TaxDistribution)
            .filter(TaxDistribution.document_id == doc.id)
            .all()
        )
        matches.append({"document": doc, "distributions": dists})

    # Get all owners for manual matching dropdown
    from app.models.owner import Owner
    owners = db.query(Owner).order_by(Owner.last_name, Owner.first_name).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "tax/matching.html",
        {
            "user": user,
            "session": ts,
            "matches": matches,
            "owners": owners,
        },
    )


@router.post("/dane/{session_id}/potvrdit/{dist_id}")
def tax_confirm_match(
    session_id: int,
    dist_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Confirm a distribution match."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    dist = db.query(TaxDistribution).filter(TaxDistribution.id == dist_id).first()
    if dist:
        dist.is_confirmed = 1
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Párování potvrzeno."}

    return RedirectResponse(url=f"/dane/{session_id}/parovani", status_code=303)


@router.post("/dane/{session_id}/prirazeni/{doc_id}")
def tax_manual_assignment(
    session_id: int,
    doc_id: int,
    request: Request,
    owner_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Manually assign a document to an owner."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    doc = db.query(TaxDocument).filter(TaxDocument.id == doc_id, TaxDocument.session_id == session_id).first()
    if doc is None:
        return HTMLResponse("Dokument nenalezen", status_code=404)

    from app.models.owner import Owner
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        request.session["flash"] = {"type": "error", "message": "Vlastník nenalezen."}
        return RedirectResponse(url=f"/dane/{session_id}/parovani", status_code=303)

    # Remove existing unconfirmed distributions for this document
    existing = db.query(TaxDistribution).filter(
        TaxDistribution.document_id == doc_id,
        TaxDistribution.is_confirmed != 1,
    ).all()
    for d in existing:
        db.delete(d)

    # Create new distribution
    dist = TaxDistribution(
        document_id=doc_id,
        owner_id=owner_id,
        matched_name=owner.display_name,
        match_score=1.0,
        is_confirmed=1,
    )
    db.add(dist)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Dokument přiřazen vlastníkovi {owner.display_name}."}
    return RedirectResponse(url=f"/dane/{session_id}/parovani", status_code=303)


@router.post("/dane/{session_id}/smazat")
def tax_delete(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a tax session with cascade."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ts = db.query(TaxSession).filter(TaxSession.id == session_id).first()
    if ts:
        db.delete(ts)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Rozúčtování smazáno."}

    return RedirectResponse(url="/dane", status_code=303)


# --- Helper functions ---


def _extract_name_from_pdf(file_path: str) -> str:
    """Extract owner name from PDF file (best-effort)."""
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if pdf.pages:
                text = pdf.pages[0].extract_text() or ""
                # Look for name patterns in first few lines
                lines = text.strip().split("\n")
                for line in lines[:10]:
                    line = line.strip()
                    # Skip empty lines and common headers
                    if not line or len(line) < 3:
                        continue
                    if any(kw in line.lower() for kw in ["rozúčtování", "příjmů", "datum", "strana", "celkem"]):
                        continue
                    # First non-header line likely contains the name
                    return line
    except Exception:
        pass

    # Fallback: try to extract name from filename
    basename = os.path.splitext(os.path.basename(file_path))[0]
    # Remove common prefixes/suffixes
    for prefix in ["rozuctovani_", "dane_", "tax_"]:
        if basename.lower().startswith(prefix):
            basename = basename[len(prefix):]
    return basename.replace("_", " ").replace("-", " ").strip()


def _auto_match_document(db: Session, doc: TaxDocument) -> None:
    """Auto-match document to owners using fuzzy matching."""
    from difflib import SequenceMatcher
    from app.models.owner import Owner

    extracted = doc.extracted_name
    if not extracted:
        return

    owners = db.query(Owner).all()
    best_match = None
    best_score = 0.0

    for owner in owners:
        display = owner.display_name
        # Compare both orderings: "First Last" and "Last First"
        score1 = SequenceMatcher(None, extracted.lower(), display.lower()).ratio()
        reversed_name = f"{owner.last_name} {owner.first_name}"
        score2 = SequenceMatcher(None, extracted.lower(), reversed_name.lower()).ratio()
        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_match = owner

    # Use threshold from PRD: 0.6 within unit, 0.75 global
    threshold = 0.6
    if best_match and best_score >= threshold:
        dist = TaxDistribution(
            document_id=doc.id,
            owner_id=best_match.id,
            matched_name=best_match.display_name,
            match_score=best_score,
        )
        db.add(dist)
