"""Sync (Synchronizace) routes — CSV upload, comparison, update."""
import csv
import io
import json
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.sync import SyncSession, SyncRecord

router = APIRouter()

_SYNC_TEMP_DIR = os.path.join(settings.UPLOAD_DIR, "_sync_import_temp")
os.makedirs(_SYNC_TEMP_DIR, exist_ok=True)


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
    """Step 1: Upload CSV → save to temp → detect columns → show mapping form."""
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

    # Save CSV to temp file
    token = str(uuid.uuid4())
    temp_path = os.path.join(_SYNC_TEMP_DIR, f"{token}.csv")
    real_path = os.path.realpath(temp_path)
    real_dir = os.path.realpath(_SYNC_TEMP_DIR)
    if not real_path.startswith(real_dir + os.sep):
        request.session["flash"] = {"type": "error", "message": "Neplatná cesta souboru."}
        return RedirectResponse(url="/synchronizace/nova", status_code=303)

    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Parse headers and sample rows
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = reader.fieldnames or []

    if not headers:
        os.remove(temp_path)
        request.session["flash"] = {"type": "error", "message": "CSV soubor neobsahuje žádné hlavičky."}
        return RedirectResponse(url="/synchronizace/nova", status_code=303)

    # Read sample rows for preview (first 5)
    sample_rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        sample_rows.append(row)

    # Count total rows
    text_io = io.StringIO(text)
    total_reader = csv.DictReader(text_io, delimiter=delimiter)
    total_rows = sum(1 for _ in total_reader)

    # Auto-detect column mapping
    auto_mapping = _detect_columns(headers)

    # Store session data
    session_name = name or file.filename or "Synchronizace"
    request.session["sync_import_token"] = token
    request.session["sync_import_name"] = session_name
    request.session["sync_import_format"] = source_format
    request.session["sync_import_delimiter"] = delimiter

    return request.app.state.templates.TemplateResponse(
        request,
        "sync/column_mapping.html",
        {
            "user": user,
            "session_name": session_name,
            "source_format": source_format,
            "headers": headers,
            "sample_rows": sample_rows,
            "total_rows": total_rows,
            "auto_mapping": auto_mapping,
        },
    )


@router.post("/synchronizace/nova/potvrdit")
async def sync_confirm_mapping(
    request: Request,
    db: Session = Depends(get_db),
):
    """Step 2: Use confirmed mapping to parse CSV and create SyncSession + SyncRecords."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    token = request.session.pop("sync_import_token", "")
    session_name = request.session.pop("sync_import_name", "Synchronizace")
    source_format = request.session.pop("sync_import_format", "interní")
    delimiter = request.session.pop("sync_import_delimiter", ";")

    if not token:
        request.session["flash"] = {"type": "error", "message": "Žádná data k importu. Nahrajte CSV znovu."}
        return RedirectResponse(url="/synchronizace/nova", status_code=303)

    temp_path = os.path.join(_SYNC_TEMP_DIR, f"{token}.csv")
    if not os.path.exists(temp_path):
        request.session["flash"] = {"type": "error", "message": "Soubor importu nenalezen. Nahrajte CSV znovu."}
        return RedirectResponse(url="/synchronizace/nova", status_code=303)

    # Read user-confirmed mapping from form
    form = await request.form()
    unit_col = str(form.get("unit_col", ""))
    owner_col = str(form.get("owner_col", ""))
    first_name_col = str(form.get("first_name_col", ""))
    last_name_col = str(form.get("last_name_col", ""))
    share_col = str(form.get("share_col", ""))

    # Read CSV from temp file
    with open(temp_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Clean up temp file
    try:
        os.remove(temp_path)
    except OSError:
        pass

    # Create sync session
    ss = SyncSession(name=session_name, source_format=source_format)
    db.add(ss)
    db.flush()

    # Parse CSV with confirmed mapping
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    from app.models.owner import Owner, Unit, OwnerUnit

    record_count = 0
    for row in reader:
        csv_unit = row.get(unit_col, "").strip() if unit_col else ""

        # Build owner name: combined column or first+last
        if owner_col:
            csv_owner = row.get(owner_col, "").strip()
        elif first_name_col or last_name_col:
            fn = row.get(first_name_col, "").strip() if first_name_col else ""
            ln = row.get(last_name_col, "").strip() if last_name_col else ""
            csv_owner = f"{ln} {fn}".strip()
        else:
            csv_owner = ""

        csv_share = row.get(share_col, "").strip() if share_col else ""

        if not csv_unit and not csv_owner:
            continue

        # Find unit in DB
        unit = None
        if csv_unit:
            # Try exact match on unit_number
            try:
                unit_num = int(csv_unit)
                unit = db.query(Unit).filter(Unit.unit_number == unit_num).first()
            except (ValueError, TypeError):
                # Try string match (e.g. "123/4")
                unit = db.query(Unit).filter(Unit.unit_number == csv_unit).first()

        # Find DB owner for this unit
        db_owner_name = ""
        db_share = ""
        csv_data_json = json.dumps(dict(row), ensure_ascii=False)
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
            csv_data=csv_data_json,
        )
        db.add(record)
        record_count += 1

    db.commit()

    if record_count == 0:
        request.session["flash"] = {
            "type": "error",
            "message": f"Synchronizace '{session_name}' vytvořena, ale nebyly naparsovány žádné záznamy.",
        }
    else:
        request.session["flash"] = {"type": "success", "message": f"Synchronizace '{session_name}' vytvořena — {record_count} záznamů."}
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


def _require_editor_sync(request: Request, db: Session):
    """Check that current user has editor or admin role for sync operations."""
    user = get_current_user(request, db)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=303)
    if user.role not in ("admin", "editor"):
        request.session["flash"] = {"type": "error", "message": "Nemáte oprávnění pro výměnu vlastníků."}
        return None, RedirectResponse(url="/synchronizace", status_code=303)
    return user, None


@router.get("/synchronizace/{session_id}/vymena/{rec_id}", response_class=HTMLResponse)
def sync_exchange_preview(
    session_id: int, rec_id: int, request: Request, db: Session = Depends(get_db)
):
    """Preview owner exchange for a sync record."""
    user, redirect = _require_editor_sync(request, db)
    if redirect:
        return redirect

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

    from datetime import date
    return request.app.state.templates.TemplateResponse(
        request,
        "sync/exchange_preview.html",
        {
            "user": user,
            "session": ss,
            "record": rec,
            "unit": unit,
            "candidates": candidates[:10],
            "today": date.today().isoformat(),
        },
    )


@router.post("/synchronizace/{session_id}/vymena/{rec_id}/potvrdit")
async def sync_exchange_confirm(
    session_id: int,
    rec_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Confirm owner exchange — set valid_to on old OwnerUnit, create new one."""
    user, redirect = _require_editor_sync(request, db)
    if redirect:
        return redirect

    form = await request.form()
    new_owner_id = int(form.get("new_owner_id", 0))
    exchange_date_str = str(form.get("exchange_date", ""))

    rec = db.query(SyncRecord).filter(
        SyncRecord.id == rec_id, SyncRecord.session_id == session_id
    ).first()
    if rec is None:
        request.session["flash"] = {"type": "error", "message": "Záznam nenalezen."}
        return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)

    from app.models.owner import Owner, OwnerUnit
    from app.models.common import AuditLog, ImportLog
    from datetime import date

    # Parse exchange date or default to today
    exchange_date = date.today()
    if exchange_date_str:
        try:
            parts = exchange_date_str.split("-")
            exchange_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass

    # Validate new_owner_id exists and is active
    new_owner = db.query(Owner).filter(Owner.id == new_owner_id, Owner.is_active == True).first()  # noqa: E712
    if new_owner is None:
        request.session["flash"] = {"type": "error", "message": "Vybraný vlastník neexistuje nebo není aktivní."}
        return RedirectResponse(url=f"/synchronizace/{session_id}/vymena/{rec_id}", status_code=303)

    old_owner_names = []
    # Soft-delete old OwnerUnit
    if rec.unit_id:
        old_ous = db.query(OwnerUnit).filter(
            OwnerUnit.unit_id == rec.unit_id,
            OwnerUnit.valid_to.is_(None),
        ).all()
        for ou in old_ous:
            ou.valid_to = exchange_date
            old_owner_names.append(str(ou.owner_id))

        # Create new OwnerUnit
        new_ou = OwnerUnit(
            owner_id=new_owner_id,
            unit_id=rec.unit_id,
            valid_from=exchange_date,
        )
        db.add(new_ou)

    rec.is_resolved = 1

    # Create AuditLog entry
    audit = AuditLog(
        user_id=user.id if user else None,
        action="exchange",
        model_name="OwnerUnit",
        record_id=rec.unit_id,
        old_value=f"unit_id={rec.unit_id}, owners=[{','.join(old_owner_names)}]",
        new_value=f"unit_id={rec.unit_id}, new_owner_id={new_owner_id}, date={exchange_date}",
    )
    db.add(audit)

    # Create ImportLog entry
    import_log = ImportLog(
        source="exchange",
        filename=f"sync_session_{session_id}",
        records_count=1,
        status="success",
        details=f"Exchange: unit {rec.unit_id}, {rec.db_owner_name} → {new_owner.display_name}",
    )
    db.add(import_log)

    db.commit()

    request.session["flash"] = {"type": "success", "message": "Výměna vlastníka provedena."}
    return RedirectResponse(url=f"/synchronizace/{session_id}", status_code=303)


@router.post("/synchronizace/{session_id}/vymena-hromadna", response_class=HTMLResponse)
def sync_bulk_exchange_preview(
    session_id: int, request: Request, db: Session = Depends(get_db)
):
    """Preview bulk owner exchange for all differing records."""
    user, redirect = _require_editor_sync(request, db)
    if redirect:
        return redirect

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
    user, redirect = _require_editor_sync(request, db)
    if redirect:
        return redirect

    from app.models.owner import Owner, OwnerUnit
    from app.models.common import AuditLog, ImportLog
    from datetime import date
    from difflib import SequenceMatcher

    records = db.query(SyncRecord).filter(
        SyncRecord.session_id == session_id,
        SyncRecord.status == "rozdílní",
        SyncRecord.is_resolved == 0,
    ).all()

    # Query all active owners ONCE (fix O(N*M) → O(N+M))
    all_owners = db.query(Owner).filter(Owner.is_active == True).all()  # noqa: E712

    exchanged = 0
    for rec in records:
        if not rec.unit_id or not rec.csv_owner_name:
            continue

        # Find best matching owner from pre-fetched list
        best_match = None
        best_score = 0.0
        for owner in all_owners:
            score = SequenceMatcher(None, rec.csv_owner_name.lower(), owner.display_name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = owner

        if best_match and best_score >= 0.9:
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

            # AuditLog for each exchange
            audit = AuditLog(
                user_id=user.id if user else None,
                action="exchange",
                model_name="OwnerUnit",
                record_id=rec.unit_id,
                old_value=f"unit_id={rec.unit_id}, old_owner={rec.db_owner_name}",
                new_value=f"unit_id={rec.unit_id}, new_owner={best_match.display_name}, score={best_score:.2f}",
            )
            db.add(audit)

    # ImportLog for bulk exchange
    if exchanged > 0:
        import_log = ImportLog(
            source="exchange",
            filename=f"sync_session_{session_id}_bulk",
            records_count=exchanged,
            status="success",
            details=f"Bulk exchange: {exchanged} records",
        )
        db.add(import_log)

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
    """Detect unit/owner/share columns from CSV headers.

    Returns dict with keys: unit, owner (or first_name + last_name), share.
    Values are the original header strings to use with csv.DictReader.

    Supports multiple formats:
    - Czech: "Jednotka", "Vlastník", "Podíl", "Číslo jednotky"
    - Internal export: "unit_number", "Příjmení", "Jméno"
    - sousede.cz: "Vlastníci jednotky"
    """
    mapping = {}
    for h in headers:
        hl = h.lower().strip()
        # Unit column
        if "unit" not in mapping and any(kw in hl for kw in [
            "jednotka", "unit_number", "unit", "byt",
            "číslo jednotky", "cislo jednotky", "č. jednotky",
            "číslo", "cislo",
        ]):
            mapping["unit"] = h

    for h in headers:
        hl = h.lower().strip()
        # Owner column (combined name)
        if "owner" not in mapping and any(kw in hl for kw in [
            "vlastník", "vlastnik", "vlastníci jednotky", "vlastnici jednotky",
            "owner", "jméno a příjmení", "jmeno a prijmeni", "name_with_titles",
        ]):
            mapping["owner"] = h

    # If no combined owner column, look for first_name + last_name
    if "owner" not in mapping:
        for h in headers:
            hl = h.lower().strip()
            if "last_name" not in mapping and any(kw in hl for kw in [
                "příjmení", "prijmeni", "last_name", "lastname",
            ]):
                mapping["last_name"] = h
            elif "first_name" not in mapping and any(kw in hl for kw in [
                "jméno", "jmeno", "first_name", "firstname",
            ]):
                mapping["first_name"] = h

    for h in headers:
        hl = h.lower().strip()
        # Share column
        if "share" not in mapping and any(kw in hl for kw in [
            "podíl", "podil", "share", "sčd", "scd",
            "votes", "hlasy", "podíl sčd",
        ]):
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
