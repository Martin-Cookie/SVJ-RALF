"""Sync (Synchronizace) routes — CSV upload, comparison, update."""
import csv
import io
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.sync import SyncSession, SyncRecord

router = APIRouter()


@router.get("/synchronizace", response_class=HTMLResponse)
def sync_list(request: Request, db: Session = Depends(get_db)):
    """List all sync sessions."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    sessions = db.query(SyncSession).order_by(SyncSession.created_at.desc()).all()

    # Count records per session
    session_data = []
    for s in sessions:
        total = db.query(SyncRecord).filter(SyncRecord.session_id == s.id).count()
        matches = db.query(SyncRecord).filter(
            SyncRecord.session_id == s.id, SyncRecord.status == "shoda"
        ).count()
        session_data.append({"session": s, "total": total, "matches": matches})

    return request.app.state.templates.TemplateResponse(
        request,
        "sync/list.html",
        {"user": user, "session_data": session_data},
    )


@router.get("/synchronizace/nova", response_class=HTMLResponse)
def sync_upload_page(request: Request, db: Session = Depends(get_db)):
    """Show CSV upload form."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    return request.app.state.templates.TemplateResponse(
        request, "sync/upload.html", {"user": user}
    )


@router.post("/synchronizace/nova")
async def sync_upload_csv(
    request: Request,
    name: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload CSV and compare with DB."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    content = await file.read()

    # Strip BOM
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]

    text = content.decode("utf-8", errors="replace")

    # Detect delimiter
    delimiter = ";"
    if text.count(",") > text.count(";"):
        delimiter = ","

    # Auto-detect format
    source_format = "interní"
    if "sousede" in text.lower() or "katastral" in text.lower():
        source_format = "sousede.cz"

    session_name = name or file.filename or "Synchronizace"
    ss = SyncSession(name=session_name, source_format=source_format)
    db.add(ss)
    db.flush()

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    # Normalize headers
    fieldnames = reader.fieldnames or []
    header_map = _detect_columns(fieldnames)

    from app.models.owner import Owner, Unit, OwnerUnit
    from difflib import SequenceMatcher

    for row in reader:
        unit_col = header_map.get("unit", "")
        owner_col = header_map.get("owner", "")
        share_col = header_map.get("share", "")

        csv_unit = row.get(unit_col, "").strip() if unit_col else ""
        csv_owner = row.get(owner_col, "").strip() if owner_col else ""
        csv_share = row.get(share_col, "").strip() if share_col else ""

        if not csv_unit and not csv_owner:
            continue

        # Find unit in DB
        unit = None
        if csv_unit:
            try:
                unit_num = int(csv_unit)
                unit = db.query(Unit).filter(Unit.unit_number == unit_num).first()
            except (ValueError, TypeError):
                pass

        # Find DB owner for this unit
        db_owner_name = ""
        db_share = ""
        if unit:
            ou = (
                db.query(OwnerUnit)
                .filter(OwnerUnit.unit_id == unit.id, OwnerUnit.valid_to.is_(None))
                .first()
            )
            if ou:
                owner = db.query(Owner).filter(Owner.id == ou.owner_id).first()
                if owner:
                    db_owner_name = owner.display_name
                    db_share = ou.ownership_share or ""

        # Determine status
        status = _compare_records(db_owner_name, csv_owner, db_share, csv_share)

        record = SyncRecord(
            session_id=ss.id,
            unit_id=unit.id if unit else None,
            status=status,
            db_owner_name=db_owner_name,
            csv_owner_name=csv_owner,
            db_share=db_share,
            csv_share=csv_share,
        )
        db.add(record)

    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Synchronizace '{session_name}' vytvořena."}
    return RedirectResponse(url=f"/synchronizace/{ss.id}", status_code=303)


@router.get("/synchronizace/{session_id}", response_class=HTMLResponse)
def sync_detail(
    session_id: int,
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
):
    """Show sync session detail with comparison results."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss is None:
        return HTMLResponse("Synchronizace nenalezena", status_code=404)

    query = db.query(SyncRecord).filter(SyncRecord.session_id == session_id)
    if status:
        query = query.filter(SyncRecord.status == status)
    records = query.all()

    # Count by status for filter bubbles
    all_records = db.query(SyncRecord).filter(SyncRecord.session_id == session_id).all()
    total = len(all_records)
    status_counts = {}
    for r in all_records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    return request.app.state.templates.TemplateResponse(
        request,
        "sync/detail.html",
        {
            "user": user,
            "session": ss,
            "records": records,
            "status_filter": status,
            "total": total,
            "status_counts": status_counts,
        },
    )


@router.post("/synchronizace/{session_id}/smazat")
def sync_delete(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a sync session with cascade."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss:
        db.delete(ss)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Synchronizace smazána."}

    return RedirectResponse(url="/synchronizace", status_code=303)


# --- Helper functions ---


def _detect_columns(headers: list) -> dict:
    """Detect unit/owner/share columns from CSV headers."""
    mapping = {}
    for h in headers:
        hl = h.lower().strip()
        if any(kw in hl for kw in ["jednotka", "unit", "byt", "číslo"]):
            mapping["unit"] = h
        elif any(kw in hl for kw in ["vlastník", "vlastnik", "jméno", "jmeno", "owner"]):
            mapping["owner"] = h
        elif any(kw in hl for kw in ["podíl", "podil", "share", "sčd"]):
            mapping["share"] = h
    return mapping


def _compare_records(db_name: str, csv_name: str, db_share: str, csv_share: str) -> str:
    """Compare DB and CSV records, return status."""
    from difflib import SequenceMatcher

    if not db_name and not csv_name:
        return "chybí"
    if not db_name:
        return "chybí"

    # Normalize for comparison
    dn = db_name.strip().lower()
    cn = csv_name.strip().lower()

    if dn == cn:
        if db_share == csv_share:
            return "shoda"
        else:
            return "rozdílné_podíly"

    # Check reversed name
    parts = cn.split()
    if len(parts) == 2:
        reversed_cn = f"{parts[1]} {parts[0]}".lower()
        if dn == reversed_cn:
            if db_share == csv_share:
                return "přeházená"
            else:
                return "rozdílné_podíly"

    # Fuzzy match
    score = SequenceMatcher(None, dn, cn).ratio()
    if score >= 0.75:
        return "částečná"

    return "rozdílní"
