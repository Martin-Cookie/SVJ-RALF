"""Sync (Synchronizace) routes — CSV upload, comparison, update."""
import csv
import io
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
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
                    db_share = str(ou.votes) if ou.votes else ""

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


@router.post("/synchronizace/{session_id}/prijmout/{rec_id}")
def sync_accept_record(
    session_id: int, rec_id: int, request: Request, db: Session = Depends(get_db)
):
    """Accept (mark as resolved) a sync record."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    rec = db.query(SyncRecord).filter(
        SyncRecord.id == rec_id, SyncRecord.session_id == session_id
    ).first()
    if rec:
        rec.is_resolved = 1
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Záznam přijat."}

    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/odmitnout/{rec_id}")
def sync_reject_record(
    session_id: int, rec_id: int, request: Request, db: Session = Depends(get_db)
):
    """Reject (mark as resolved/rejected) a sync record."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    rec = db.query(SyncRecord).filter(
        SyncRecord.id == rec_id, SyncRecord.session_id == session_id
    ).first()
    if rec:
        rec.is_resolved = 1
        rec.status = "odmítnuto"
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Záznam odmítnut."}

    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/aktualizovat")
async def sync_selective_update(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Apply selective updates from CSV for selected records."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    record_ids = form.getlist("record_ids")

    updated = 0
    for rid_str in record_ids:
        try:
            rid = int(rid_str)
        except (ValueError, TypeError):
            continue

        rec = db.query(SyncRecord).filter(
            SyncRecord.id == rid, SyncRecord.session_id == session_id
        ).first()
        if rec and rec.unit_id:
            # Update owner name from CSV if different
            from app.models.owner import Owner, OwnerUnit
            ou = db.query(OwnerUnit).filter(
                OwnerUnit.unit_id == rec.unit_id, OwnerUnit.valid_to.is_(None)
            ).first()
            if ou:
                owner = db.query(Owner).filter(Owner.id == ou.owner_id).first()
                if owner and rec.csv_owner_name:
                    # Update share if different
                    if rec.csv_share:
                        try:
                            ou.votes = int(rec.csv_share)
                        except (ValueError, TypeError):
                            pass
                rec.is_resolved = 1
                updated += 1

    db.commit()
    request.session["flash"] = {"type": "success", "message": f"Aktualizováno {updated} záznamů."}
    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/aplikovat-kontakty")
def sync_apply_contacts(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Transfer contact info from CSV records to DB owners."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss is None:
        return HTMLResponse("Synchronizace nenalezena", status_code=404)

    # Mark all unresolved records as resolved for contact transfer
    records = db.query(SyncRecord).filter(
        SyncRecord.session_id == session_id,
        SyncRecord.is_resolved == 0,
    ).all()

    transferred = 0
    for rec in records:
        if rec.csv_data:
            import json
            try:
                csv_row = json.loads(rec.csv_data)
                # Transfer email/phone if available
                if rec.unit_id:
                    from app.models.owner import OwnerUnit, Owner
                    ou = db.query(OwnerUnit).filter(
                        OwnerUnit.unit_id == rec.unit_id, OwnerUnit.valid_to.is_(None)
                    ).first()
                    if ou:
                        owner = db.query(Owner).filter(Owner.id == ou.owner_id).first()
                        if owner:
                            for key in ["email", "telefon", "phone"]:
                                if key in csv_row and csv_row[key]:
                                    if key in ("telefon", "phone"):
                                        owner.phone = csv_row[key]
                                    else:
                                        owner.email = csv_row[key]
                                    transferred += 1
            except (json.JSONDecodeError, TypeError):
                pass

    db.commit()
    request.session["flash"] = {"type": "success", "message": f"Kontakty přeneseny ({transferred})."}
    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.get("/synchronizace/{session_id}/vymena/{rec_id}", response_class=HTMLResponse)
def sync_exchange_preview(
    session_id: int, rec_id: int, request: Request, db: Session = Depends(get_db)
):
    """Preview owner exchange for a sync record."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss is None:
        return HTMLResponse("Synchronizace nenalezena", status_code=404)

    rec = db.query(SyncRecord).filter(
        SyncRecord.id == rec_id, SyncRecord.session_id == session_id
    ).first()
    if rec is None:
        return HTMLResponse("Záznam nenalezen", status_code=404)

    # Find potential matches for new owner
    from app.models.owner import Owner, Unit, OwnerUnit
    from difflib import SequenceMatcher

    candidates = []
    if rec.csv_owner_name:
        owners = db.query(Owner).filter(Owner.is_active == True).all()  # noqa: E712
        for owner in owners:
            score = SequenceMatcher(None, rec.csv_owner_name.lower(), owner.display_name.lower()).ratio()
            if score >= 0.5:
                candidates.append({"owner": owner, "score": score})
        candidates.sort(key=lambda x: x["score"], reverse=True)

    unit = db.query(Unit).filter(Unit.id == rec.unit_id).first() if rec.unit_id else None

    return request.app.state.templates.TemplateResponse(
        request,
        "sync/exchange_preview.html",
        {
            "user": user,
            "session": ss,
            "record": rec,
            "unit": unit,
            "candidates": candidates[:10],
        },
    )


@router.post("/synchronizace/{session_id}/vymena/{rec_id}/potvrdit")
def sync_exchange_confirm(
    session_id: int,
    rec_id: int,
    request: Request,
    new_owner_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Confirm owner exchange — set valid_to on old OwnerUnit, create new one."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    rec = db.query(SyncRecord).filter(
        SyncRecord.id == rec_id, SyncRecord.session_id == session_id
    ).first()
    if rec is None:
        request.session["flash"] = {"type": "error", "message": "Záznam nenalezen."}
        return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)

    from app.models.owner import Owner, OwnerUnit
    from datetime import date

    # Soft-delete old OwnerUnit
    if rec.unit_id:
        old_ous = db.query(OwnerUnit).filter(
            OwnerUnit.unit_id == rec.unit_id,
            OwnerUnit.valid_to.is_(None),
        ).all()
        for ou in old_ous:
            ou.valid_to = date.today()

        # Create new OwnerUnit
        new_ou = OwnerUnit(
            owner_id=new_owner_id,
            unit_id=rec.unit_id,
            valid_from=date.today(),
        )
        db.add(new_ou)

    rec.is_resolved = 1
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Výměna vlastníka provedena."}
    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/vymena-hromadna", response_class=HTMLResponse)
def sync_bulk_exchange_preview(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Preview bulk owner exchange for all differing records."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss is None:
        return HTMLResponse("Synchronizace nenalezena", status_code=404)

    records = db.query(SyncRecord).filter(
        SyncRecord.session_id == session_id,
        SyncRecord.status == "rozdílní",
        SyncRecord.is_resolved == 0,
    ).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "sync/exchange_bulk.html",
        {"user": user, "session": ss, "records": records},
    )


@router.post("/synchronizace/{session_id}/vymena-hromadna/potvrdit")
def sync_bulk_exchange_confirm(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Confirm bulk owner exchange for all differing records."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    from app.models.owner import Owner, OwnerUnit
    from datetime import date
    from difflib import SequenceMatcher

    records = db.query(SyncRecord).filter(
        SyncRecord.session_id == session_id,
        SyncRecord.status == "rozdílní",
        SyncRecord.is_resolved == 0,
    ).all()

    exchanged = 0
    for rec in records:
        if not rec.unit_id or not rec.csv_owner_name:
            continue

        # Find best matching owner
        owners = db.query(Owner).filter(Owner.is_active == True).all()  # noqa: E712
        best_match = None
        best_score = 0.0
        for owner in owners:
            score = SequenceMatcher(None, rec.csv_owner_name.lower(), owner.display_name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = owner

        if best_match and best_score >= 0.75:
            # Soft-delete old
            old_ous = db.query(OwnerUnit).filter(
                OwnerUnit.unit_id == rec.unit_id,
                OwnerUnit.valid_to.is_(None),
            ).all()
            for ou in old_ous:
                ou.valid_to = date.today()

            # Create new
            new_ou = OwnerUnit(
                owner_id=best_match.id,
                unit_id=rec.unit_id,
                valid_from=date.today(),
            )
            db.add(new_ou)
            rec.is_resolved = 1
            exchanged += 1

    db.commit()
    request.session["flash"] = {"type": "success", "message": f"Hromadná výměna: {exchanged} záznamů."}
    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/exportovat")
def sync_export(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Export sync comparison to Excel."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ss = db.query(SyncSession).filter(SyncSession.id == session_id).first()
    if ss is None:
        return HTMLResponse("Synchronizace nenalezena", status_code=404)

    records = db.query(SyncRecord).filter(SyncRecord.session_id == session_id).all()

    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Synchronizace"
    ws.append(["Jednotka", "Vlastník (DB)", "Vlastník (CSV)", "Podíl (DB)", "Podíl (CSV)", "Status"])

    for rec in records:
        unit_num = ""
        if rec.unit_id:
            from app.models.owner import Unit
            unit = db.query(Unit).filter(Unit.id == rec.unit_id).first()
            if unit:
                unit_num = str(unit.unit_number)
        ws.append([
            unit_num, rec.db_owner_name, rec.csv_owner_name,
            rec.db_share, rec.csv_share, rec.status,
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=synchronizace_{session_id}.xlsx"},
    )


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
