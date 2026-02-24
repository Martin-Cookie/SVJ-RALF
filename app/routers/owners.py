"""Owner management routes."""
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.owner import Owner, OwnerUnit, Unit
from app.models.common import ImportLog

# Temp directory for uploaded Excel files
_IMPORT_TEMP_DIR = os.path.join(settings.UPLOAD_DIR, "_import_temp")
os.makedirs(_IMPORT_TEMP_DIR, exist_ok=True)

router = APIRouter()


@router.get("/vlastnici", response_class=HTMLResponse)
def owners_list(
    request: Request,
    search: str = "",
    typ: str = "",
    vlastnictvi: str = "",
    kontakt: str = "",
    sort: str = "name",
    db: Session = Depends(get_db),
):
    """List all owners with search/filter/sort."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Owner).filter(Owner.is_active == True).options(  # noqa: E712
        selectinload(Owner.owner_units).selectinload(OwnerUnit.unit)
    )

    # Search filter — uses name_normalized for diacritics-insensitive search
    if search:
        term = f"%{search}%"
        query = query.filter(
            (Owner.first_name.ilike(term))
            | (Owner.last_name.ilike(term))
            | (Owner.name_with_titles.ilike(term))
            | (Owner.name_normalized.ilike(term))
            | (Owner.email.ilike(term))
            | (Owner.company_id.ilike(term))
        )

    # Type filter
    if typ:
        query = query.filter(Owner.owner_type == typ)

    # Ownership type filter (SJM, VL, SJVL, etc.)
    if vlastnictvi:
        query = query.filter(
            Owner.id.in_(
                db.query(OwnerUnit.owner_id)
                .filter(OwnerUnit.ownership_type == vlastnictvi, OwnerUnit.valid_to.is_(None))
            )
        )

    # Contact filter
    if kontakt == "s_emailem":
        query = query.filter(Owner.email != "", Owner.email.isnot(None))
    elif kontakt == "bez_emailu":
        query = query.filter((Owner.email == "") | (Owner.email.is_(None)))
    elif kontakt == "s_telefonem":
        query = query.filter(Owner.phone != "", Owner.phone.isnot(None))
    elif kontakt == "bez_telefonu":
        query = query.filter((Owner.phone == "") | (Owner.phone.is_(None)))

    # Sorting
    sort_map = {
        "name": Owner.name_normalized.asc(),
        "last_name": Owner.last_name.asc(),
        "first_name": Owner.first_name.asc(),
        "created_at": Owner.created_at.desc(),
    }
    order = sort_map.get(sort, Owner.name_normalized.asc())
    query = query.order_by(order)

    owners = query.all()

    # Count by type for filter bubbles
    active_q = db.query(Owner).filter(Owner.is_active == True)  # noqa: E712
    total = active_q.count()
    fyzicka_count = active_q.filter(Owner.owner_type == "physical").count()
    pravnicka_count = active_q.filter(Owner.owner_type == "legal").count()

    # Contact counts
    s_emailem_count = db.query(Owner).filter(
        Owner.is_active == True, Owner.email != "", Owner.email.isnot(None)  # noqa: E712
    ).count()
    bez_emailu_count = total - s_emailem_count
    s_telefonem_count = db.query(Owner).filter(
        Owner.is_active == True, Owner.phone != "", Owner.phone.isnot(None)  # noqa: E712
    ).count()
    bez_telefonu_count = total - s_telefonem_count

    # Distinct ownership types for filter dropdown
    ownership_types = [
        r[0] for r in db.query(OwnerUnit.ownership_type).filter(
            OwnerUnit.ownership_type.isnot(None),
            OwnerUnit.ownership_type != "",
            OwnerUnit.valid_to.is_(None),
        ).distinct().order_by(OwnerUnit.ownership_type).all()
    ]

    # Build current filter URL for back_url chain
    filter_params = []
    if search:
        filter_params.append(f"search={search}")
    if typ:
        filter_params.append(f"typ={typ}")
    if vlastnictvi:
        filter_params.append(f"vlastnictvi={vlastnictvi}")
    if kontakt:
        filter_params.append(f"kontakt={kontakt}")
    if sort != "name":
        filter_params.append(f"sort={sort}")
    current_url = "/vlastnici" + ("?" + "&".join(filter_params) if filter_params else "")

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/list.html",
        {
            "user": user,
            "owners": owners,
            "search": search,
            "typ": typ,
            "vlastnictvi": vlastnictvi,
            "kontakt": kontakt,
            "sort": sort,
            "total": total,
            "fyzicka_count": fyzicka_count,
            "pravnicka_count": pravnicka_count,
            "s_emailem_count": s_emailem_count,
            "bez_emailu_count": bez_emailu_count,
            "s_telefonem_count": s_telefonem_count,
            "bez_telefonu_count": bez_telefonu_count,
            "current_url": current_url,
            "ownership_types": ownership_types,
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
        .order_by(Owner.name_normalized)
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
    """Upload Excel file, save to disk, show preview."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    from app.services.excel_import import preview_owners_from_excel

    # Save uploaded file to temp directory
    token = str(uuid.uuid4())
    temp_path = os.path.join(_IMPORT_TEMP_DIR, f"{token}.xlsx")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse and preview
    result = preview_owners_from_excel(temp_path)

    imports = (
        db.query(ImportLog)
        .filter(ImportLog.source == "excel-owners")
        .order_by(ImportLog.created_at.desc())
        .all()
    )

    # Store token in session for confirm step
    if result["rows_processed"] > 0:
        request.session["import_token"] = token
        request.session["import_filename"] = file.filename or "import.xlsx"

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/import.html",
        {
            "user": user,
            "imports": imports,
            "preview": result,
            "errors": result["errors"],
        },
    )


@router.post("/vlastnici/import/potvrdit")
def import_confirm(request: Request, db: Session = Depends(get_db)):
    """Confirm and execute the import from the saved Excel file."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    from app.services.excel_import import import_owners_from_excel

    token = request.session.pop("import_token", "")
    filename = request.session.pop("import_filename", "import.xlsx")

    if not token:
        request.session["flash"] = {"type": "error", "message": "Žádná data k importu."}
        return RedirectResponse(url="/vlastnici/import", status_code=303)

    temp_path = os.path.join(_IMPORT_TEMP_DIR, f"{token}.xlsx")
    if not os.path.exists(temp_path):
        request.session["flash"] = {"type": "error", "message": "Soubor importu nenalezen."}
        return RedirectResponse(url="/vlastnici/import", status_code=303)

    try:
        # Run the actual import
        result = import_owners_from_excel(db, temp_path)

        # Create import log
        log = ImportLog(
            source="excel-owners",
            filename=filename,
            records_count=result["rows_processed"],
            status="success",
        )
        db.add(log)
        db.commit()

        request.session["flash"] = {
            "type": "success",
            "message": (
                f"Import dokončen: {result['owners_created']} vlastníků, "
                f"{result['units_created']} jednotek, "
                f"{result['links_created']} vazeb."
            ),
        }
    except Exception as e:
        db.rollback()
        request.session["flash"] = {"type": "error", "message": f"Chyba importu: {e}"}
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
    owner_id: int, request: Request, back_url: str = "", db: Session = Depends(get_db)
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

    # Sanitize back_url: must start with / and not contain protocol
    if back_url and (not back_url.startswith("/") or "://" in back_url):
        back_url = ""

    return request.app.state.templates.TemplateResponse(
        request,
        "owners/detail.html",
        {
            "user": user,
            "owner": owner,
            "owner_units": owner_units,
            "history_units": history_units,
            "available_units": available_units,
            "back_url": back_url,
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


@router.get("/vlastnici/{owner_id}/adresa/{prefix}/upravit-formular", response_class=HTMLResponse)
def owner_address_edit_form(
    owner_id: int, prefix: str, request: Request, db: Session = Depends(get_db)
):
    """HTMX: return address edit form partial for perm or corr address."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    if prefix not in ("perm", "corr"):
        return HTMLResponse("Neplatný prefix adresy", status_code=404)
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/owner_address_form.html",
        {"owner": owner, "prefix": prefix},
    )


@router.get("/vlastnici/{owner_id}/adresa/{prefix}/info", response_class=HTMLResponse)
def owner_address_info(
    owner_id: int, prefix: str, request: Request, db: Session = Depends(get_db)
):
    """HTMX: return address display partial for perm or corr address."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    if prefix not in ("perm", "corr"):
        return HTMLResponse("Neplatný prefix adresy", status_code=404)
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/owner_address_display.html",
        {"owner": owner, "prefix": prefix},
    )


@router.post("/vlastnici/{owner_id}/adresa/{prefix}/upravit")
def owner_address_update(
    owner_id: int,
    prefix: str,
    request: Request,
    street: str = Form(""),
    city: str = Form(""),
    zip: str = Form(""),
    db: Session = Depends(get_db),
):
    """Save address (perm or corr) for an owner."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    if prefix not in ("perm", "corr"):
        return HTMLResponse("Neplatný prefix adresy", status_code=404)
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if owner is None:
        return HTMLResponse("Vlastník nenalezen", status_code=404)

    setattr(owner, f"{prefix}_street", street)
    setattr(owner, f"{prefix}_city", city)
    setattr(owner, f"{prefix}_zip", zip)
    db.commit()

    # Return HTMX display partial
    return request.app.state.templates.TemplateResponse(
        request,
        "partials/owner_address_display.html",
        {"owner": owner, "prefix": prefix},
    )


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
