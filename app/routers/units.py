"""Unit management routes."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.owner import Owner, OwnerUnit, Unit

router = APIRouter()


@router.get("/jednotky", response_class=HTMLResponse)
def units_list(
    request: Request,
    search: str = "",
    building: str = "",
    sort: str = "unit_number",
    db: Session = Depends(get_db),
):
    """List all units with search/filter/sort."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Unit)

    # Search filter
    if search:
        try:
            num = int(search)
            query = query.filter(Unit.unit_number == num)
        except ValueError:
            term = f"%{search}%"
            query = query.filter(
                (Unit.building_number.ilike(term))
                | (Unit.address.ilike(term))
                | (Unit.section.ilike(term))
            )

    # Building filter
    if building:
        query = query.filter(Unit.building_number == building)

    # Sorting
    sort_map = {
        "unit_number": Unit.unit_number.asc(),
        "building": Unit.building_number.asc(),
        "area": Unit.floor_area.desc(),
    }
    order = sort_map.get(sort, Unit.unit_number.asc())
    query = query.order_by(order)

    units = query.all()

    # Buildings for filter
    buildings = (
        db.query(Unit.building_number)
        .filter(Unit.building_number != "", Unit.building_number != None)  # noqa: E711
        .distinct()
        .order_by(Unit.building_number)
        .all()
    )
    building_list = [b[0] for b in buildings]

    total = db.query(Unit).count()

    return request.app.state.templates.TemplateResponse(
        request,
        "units/list.html",
        {
            "user": user,
            "units": units,
            "search": search,
            "building": building,
            "sort": sort,
            "total": total,
            "building_list": building_list,
        },
    )


@router.get("/jednotky/nova-formular", response_class=HTMLResponse)
def unit_create_form(request: Request, db: Session = Depends(get_db)):
    """HTMX: return new unit creation form partial."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    return request.app.state.templates.TemplateResponse(
        request, "partials/unit_form.html", {"unit": None}
    )


@router.post("/jednotky/nova")
def unit_create(
    request: Request,
    unit_number: int = Form(...),
    building_number: str = Form(""),
    space_type: str = Form(""),
    section: str = Form(""),
    floor_area: str = Form(""),
    room_count: str = Form(""),
    address: str = Form(""),
    lv_number: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new unit."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    # Check for duplicate
    existing = db.query(Unit).filter(Unit.unit_number == unit_number).first()
    if existing:
        request.session["flash"] = {"type": "error", "message": f"Jednotka č. {unit_number} již existuje."}
        return RedirectResponse(url="/jednotky", status_code=303)

    unit = Unit(
        unit_number=unit_number,
        building_number=building_number,
        space_type=space_type,
        section=section,
        floor_area=float(floor_area) if floor_area else 0.0,
        room_count=room_count,
        address=address,
        lv_number=int(lv_number) if lv_number else None,
    )
    db.add(unit)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Jednotka č. {unit_number} vytvořena."}
    return RedirectResponse(url=f"/jednotky/{unit.id}", status_code=303)


@router.get("/jednotky/{unit_id}", response_class=HTMLResponse)
def unit_detail(
    unit_id: int, request: Request, db: Session = Depends(get_db)
):
    """Show unit detail page."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("Jednotka nenalezena", status_code=404)

    # Get active owner links
    owner_units = (
        db.query(OwnerUnit)
        .filter(OwnerUnit.unit_id == unit_id, OwnerUnit.valid_to == None)  # noqa: E711
        .all()
    )

    # Ownership history
    history = (
        db.query(OwnerUnit)
        .filter(OwnerUnit.unit_id == unit_id, OwnerUnit.valid_to != None)  # noqa: E711
        .order_by(OwnerUnit.valid_to.desc())
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "units/detail.html",
        {
            "user": user,
            "unit": unit,
            "owner_units": owner_units,
            "history": history,
        },
    )


@router.get("/jednotky/{unit_id}/upravit-formular", response_class=HTMLResponse)
def unit_edit_form(unit_id: int, request: Request, db: Session = Depends(get_db)):
    """HTMX: return unit edit form partial."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request, "partials/unit_form.html", {"unit": unit}
    )


@router.get("/jednotky/{unit_id}/info", response_class=HTMLResponse)
def unit_info_display(unit_id: int, request: Request, db: Session = Depends(get_db)):
    """HTMX: return unit info display partial."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("", status_code=404)
    return request.app.state.templates.TemplateResponse(
        request, "partials/unit_info_display.html", {"unit": unit}
    )


@router.post("/jednotky/{unit_id}/upravit")
def unit_update(
    unit_id: int,
    request: Request,
    unit_number: int = Form(...),
    building_number: str = Form(""),
    space_type: str = Form(""),
    section: str = Form(""),
    floor_area: str = Form(""),
    room_count: str = Form(""),
    address: str = Form(""),
    lv_number: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update unit fields."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("Jednotka nenalezena", status_code=404)

    unit.unit_number = unit_number
    unit.building_number = building_number
    unit.space_type = space_type
    unit.section = section
    unit.floor_area = float(floor_area) if floor_area else 0.0
    unit.room_count = room_count
    unit.address = address
    unit.lv_number = int(lv_number) if lv_number else None
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Jednotka aktualizována."}
    return RedirectResponse(url=f"/jednotky/{unit_id}", status_code=303)


@router.post("/jednotky/{unit_id}/smazat")
def unit_delete(
    unit_id: int, request: Request, db: Session = Depends(get_db)
):
    """Delete unit with cascade (OwnerUnit links)."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if unit is None:
        return HTMLResponse("Jednotka nenalezena", status_code=404)

    db.delete(unit)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Jednotka č. {unit.unit_number} smazána."}
    return RedirectResponse(url="/jednotky", status_code=303)
