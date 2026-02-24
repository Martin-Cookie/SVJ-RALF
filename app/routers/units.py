"""Unit management routes."""
from fastapi import APIRouter, Depends, Request
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
                (Unit.building.ilike(term))
                | (Unit.address.ilike(term))
                | (Unit.section.ilike(term))
            )

    # Building filter
    if building:
        query = query.filter(Unit.building == building)

    # Sorting
    sort_map = {
        "unit_number": Unit.unit_number.asc(),
        "building": Unit.building.asc(),
        "area": Unit.area.desc(),
    }
    order = sort_map.get(sort, Unit.unit_number.asc())
    query = query.order_by(order)

    units = query.all()

    # Buildings for filter
    buildings = (
        db.query(Unit.building)
        .filter(Unit.building != "")
        .distinct()
        .order_by(Unit.building)
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
