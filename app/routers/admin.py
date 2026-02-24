"""Administration (Správa) routes."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.administration import SvjInfo, SvjAddress, BoardMember

router = APIRouter()


@router.get("/sprava", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    """Show administration page."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    info = db.query(SvjInfo).first()
    addresses = db.query(SvjAddress).order_by(SvjAddress.city, SvjAddress.street).all()
    board = (
        db.query(BoardMember)
        .filter(BoardMember.group == "board")
        .order_by(BoardMember.role, BoardMember.name)
        .all()
    )
    control = (
        db.query(BoardMember)
        .filter(BoardMember.group == "control")
        .order_by(BoardMember.role, BoardMember.name)
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/index.html",
        {
            "user": user,
            "info": info,
            "addresses": addresses,
            "board": board,
            "control": control,
        },
    )


@router.post("/sprava/info")
def admin_update_info(
    request: Request,
    name: str = Form(""),
    building_type: str = Form(""),
    total_shares: str = Form("0"),
    db: Session = Depends(get_db),
):
    """Update SVJ info."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    info = db.query(SvjInfo).first()
    if info is None:
        info = SvjInfo()
        db.add(info)

    info.name = name
    info.building_type = building_type
    try:
        info.total_shares = int(total_shares)
    except (ValueError, TypeError):
        info.total_shares = 0

    db.commit()
    request.session["flash"] = {"type": "success", "message": "Informace o SVJ aktualizovány."}
    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/clen")
def admin_add_member(
    request: Request,
    name: str = Form(...),
    role: str = Form("Člen"),
    group: str = Form("board"),
    email: str = Form(""),
    phone: str = Form(""),
    db: Session = Depends(get_db),
):
    """Add a board/control member."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    member = BoardMember(name=name, role=role, group=group, email=email, phone=phone)
    db.add(member)
    db.commit()

    label = "výboru" if group == "board" else "kontrolního orgánu"
    request.session["flash"] = {"type": "success", "message": f"Člen {label} přidán."}
    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/clen/{member_id}/smazat")
def admin_delete_member(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a board/control member."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    member = db.query(BoardMember).filter(BoardMember.id == member_id).first()
    if member:
        db.delete(member)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Člen smazán."}

    return RedirectResponse(url="/sprava", status_code=303)
