"""Owner management routes."""
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
from app.models.owner import Owner, OwnerUnit, Unit
from app.models.common import ImportLog

# Temp directory for import previews (cookie is too small for large datasets)
_IMPORT_TEMP_DIR = os.path.join(settings.UPLOAD_DIR, "_import_temp")
os.makedirs(_IMPORT_TEMP_DIR, exist_ok=True)

router = APIRouter()


@router.get("/vlastnici", response_class=HTMLResponse)
def owners_list(
    request: Request,
    search: str = "",
    typ: str = "",
    sort: str = "last_name",
    db: Session = Depends(get_db),
):
    """List all owners with search/filter/sort."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Owner).filter(Owner.is_active == True)  # noqa: E712

    # Search filter
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Owner.first_name.ilike(term))
            | (Owner.last_name.ilike(term))
            | (Owner.email.ilike(term))
            | (Owner.birth_number.ilike(term))
            | (Owner.ico.ilike(term))
        )

    # Type filter
    if typ:
        query = query.filter(Owner.owner_type == typ)

    # Sorting
    sort_map = {
        "last_name": Owner.last_name.asc(),
        "first_name": Owner.first_name.asc(),
        "created_at": Owner.created_at.desc(),
    }
    order = sort_map.get(sort, Owner.last_name.asc())
    query = query.order_by(order)

    owners = query.all()

    # Count by type for filter bubbles
    total = db.query(Owner).filter(Owner.is_active == True).count()  # noqa: E712
    fyzicka_count = (
        db.query(Owner)
        .filter(Owner.is_active == True, Owner.owner_type == "fyzická")  # noqa: E712
        .count()
    )
    pravnicka_count = (
        db.query(Owner)
        .filter(Owner.is_active == True, Owner.owner_type == "právnická")  # noqa: E712
        .count()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/list.html",
        {
            "user": user,
            "owners": owners,
            "search": search,
            "typ": typ,
            "sort": sort,
            "total": total,
            "fyzicka_count": fyzicka_count,
            "pravnicka_count": pravnicka_count,
        },
    )


# --- Export (must be before {owner_id}) ---


@router.get("/vlastnici/export")
def owners_export(request: Request, db: Session = Depends(get_db)):
    """Export owners to Excel."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    owners = (
        db.query(Owner)
        .filter(Owner.is_active == True)  # noqa: E712
        .order_by(Owner.last_name)
        .all()
    )

    from app.services.excel_export import export_owners_xlsx

    output = export_owners_xlsx(owners)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=vlastnici.xlsx"},
    )


# --- Import routes (must be before {owner_id}) ---


@router.get("/vlastnici/import", response_class=HTMLResponse)
def import_page(request: Request, db: Session = Depends(get_db)):
    """Show import page with upload form and import history."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    imports = (
        db.query(ImportLog)
        .filter(ImportLog.source == "excel-owners")
        .order_by(ImportLog.created_at.desc())
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/import.html",
        {"user": user, "imports": imports, "preview": None, "errors": []},
    )


@router.post("/vlastnici/import", response_class=HTMLResponse)
def import_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload Excel file and show preview."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    from app.services.excel_import import parse_owners_xlsx

    contents = file.file.read()
    rows, errors = parse_owners_xlsx(io.BytesIO(contents))

    imports = (
        db.query(ImportLog)
        .filter(ImportLog.source == "excel-owners")
        .order_by(ImportLog.created_at.desc())
        .all()
    )

    # Store parsed data in temp file (cookie session is too small for large datasets)
    if rows:
        token = str(uuid.uuid4())
        temp_path = os.path.join(_IMPORT_TEMP_DIR, f"{token}.json")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        request.session["import_token"] = token

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/import.html",
        {"user": user, "imports": imports, "preview": rows, "errors": errors},
    )


@router.post("/vlastnici/import/potvrdit")
def import_confirm(request: Request, db: Session = Depends(get_db)):
    """Confirm and execute the import."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    token = request.session.pop("import_token", "")
    rows = []
    if token:
        temp_path = os.path.join(_IMPORT_TEMP_DIR, f"{token}.json")
        if os.path.exists(temp_path):
            with open(temp_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
            os.remove(temp_path)
    if not rows:
        request.session["flash"] = {"type": "error", "message": "Žádná data k importu."}
        return RedirectResponse(url="/vlastnici/import", status_code=303)

    # Create import log
    log = ImportLog(
        source="excel-owners",
        filename="import.xlsx",
        records_count=len(rows),
        status="success",
    )
    db.add(log)
    db.flush()

    created_owners = 0
    created_units = 0

    for row in rows:
        owner = Owner(
            first_name=row.get("first_name", ""),
            last_name=row.get("last_name", ""),
            title_before=row.get("title_before", ""),
            title_after=row.get("title_after", ""),
            birth_number=row.get("birth_number", ""),
            ico=row.get("ico", ""),
            owner_type=row.get("owner_type", "fyzická"),
            email=row.get("email", ""),
            phone=row.get("phone", ""),
            perm_street=row.get("perm_street", ""),
            perm_city=row.get("perm_city", ""),
            perm_zip=row.get("perm_zip", ""),
            corr_street=row.get("corr_street", ""),
            corr_city=row.get("corr_city", ""),
            corr_zip=row.get("corr_zip", ""),
            is_active=True,
        )
        db.add(owner)
        db.flush()
        created_owners += 1

        unit_number = str(row.get("unit_number", "")).strip()
        if unit_number and unit_number != "0":
            unit = db.query(Unit).filter(Unit.unit_number == unit_number).first()
            if unit is None:
                unit = Unit(
                    unit_number=unit_number,
                    building=row.get("building", ""),
                    section=row.get("section", ""),
                    space_type=row.get("space_type", ""),
                    address=row.get("address", ""),
                    land_registry_number=row.get("land_registry_number", ""),
                    room_count=int(row.get("room_count", 0) or 0),
                    area=float(row.get("area", 0) or 0),
                    share_scd=int(float(row.get("share_scd", 0) or 0)),
                )
                db.add(unit)
                db.flush()
                created_units += 1

            ou = OwnerUnit(
                owner_id=owner.id,
                unit_id=unit.id,
                ownership_type=row.get("ownership_type", "Neuvedeno"),
                ownership_share=str(row.get("share_scd", "")),
                voting_weight=float(row.get("voting_weight", 0) or 0),
            )
            db.add(ou)

    db.commit()

    request.session["flash"] = {
        "type": "success",
        "message": f"Import dokončen: {created_owners} vlastníků, {created_units} jednotek.",
    }
    return RedirectResponse(url="/vlastnici", status_code=303)


@router.post("/vlastnici/import/{log_id}/smazat")
def import_delete(log_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete an import and cascade-delete related data."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    log = db.query(ImportLog).filter(ImportLog.id == log_id).first()
    if log:
        db.delete(log)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Import smazán."}

    return RedirectResponse(url="/vlastnici/import", status_code=303)


# --- Detail + editing routes (with {owner_id} path param) ---


@router.get("/vlastnici/{owner_id}", response_class=HTMLResponse)
def owner_detail(
    owner_id: int, request: Request, db: Session = Depends(get_db)
):
    """Show owner detail page."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)

    # Get units linked to this owner (active links only)
    owner_units = (
        db.query(OwnerUnit)
        .filter(OwnerUnit.owner_id == owner_id, OwnerUnit.valid_to == None)  # noqa: E711
        .all()
    )

    # Ownership history (expired links)
    history_units = (
        db.query(OwnerUnit)
        .filter(OwnerUnit.owner_id == owner_id, OwnerUnit.valid_to != None)  # noqa: E711
        .order_by(OwnerUnit.valid_to.desc())
        .all()
    )

    # Available units for linking
    available_units = db.query(Unit).order_by(Unit.unit_number).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/detail.html",
        {
            "user": user,
            "owner": owner,
            "owner_units": owner_units,
            "history_units": history_units,
            "available_units": available_units,
        },
    )


@router.get("/vlastnici/{owner_id}/upravit-formular", response_class=HTMLResponse)
def owner_edit_form(owner_id: int, request: Request, db: Session = Depends(get_db)):
    """HTMX: return contact edit form partial."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request, "partials/owner_contact_form.html", {"owner": owner}
    )


@router.get("/vlastnici/{owner_id}/info", response_class=HTMLResponse)
def owner_info_display(owner_id: int, request: Request, db: Session = Depends(get_db)):
    """HTMX: return contact display partial."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request, "partials/owner_contact_display.html", {"owner": owner}
    )


@router.post("/vlastnici/{owner_id}/upravit")
def owner_update(
    owner_id: int,
    request: Request,
    email: str = Form(""),
    phone: str = Form(""),
    perm_street: str = Form(""),
    perm_city: str = Form(""),
    perm_zip: str = Form(""),
    corr_street: str = Form(""),
    corr_city: str = Form(""),
    corr_zip: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update owner contact info."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)

    owner.email = email
    owner.phone = phone
    owner.perm_street = perm_street
    owner.perm_city = perm_city
    owner.perm_zip = perm_zip
    owner.corr_street = corr_street
    owner.corr_city = corr_city
    owner.corr_zip = corr_zip
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Kontaktní údaje uloženy."}
    return RedirectResponse(url=f"/vlastnici/{owner_id}", status_code=303)


@router.post("/vlastnici/{owner_id}/jednotky/pridat")
def owner_add_unit(
    owner_id: int,
    request: Request,
    unit_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Link a unit to an owner."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)

    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("Jednotka nenalezena", status_code=404)

    # Check if link already exists
    existing = (
        db.query(OwnerUnit)
        .filter(
            OwnerUnit.owner_id == owner_id,
            OwnerUnit.unit_id == unit_id,
            OwnerUnit.valid_to == None,  # noqa: E711
        )
        .first()
    )
    if existing is None:
        ou = OwnerUnit(owner_id=owner_id, unit_id=unit_id)
        db.add(ou)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Jednotka přiřazena."}
    else:
        request.session["flash"] = {"type": "info", "message": "Jednotka již přiřazena."}

    return RedirectResponse(url=f"/vlastnici/{owner_id}", status_code=303)


@router.post("/vlastnici/{owner_id}/jednotky/{ou_id}/odebrat")
def owner_remove_unit(
    owner_id: int,
    ou_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove (soft-delete) a unit link from an owner."""
    from datetime import date

    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    ou = (
        db.query(OwnerUnit)
        .filter(OwnerUnit.id == ou_id, OwnerUnit.owner_id == owner_id)
        .first()
    )
    if ou:
        ou.valid_to = date.today()
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Jednotka odebrána."}

    return RedirectResponse(url=f"/vlastnici/{owner_id}", status_code=303)
