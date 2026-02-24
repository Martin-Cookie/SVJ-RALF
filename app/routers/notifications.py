"""Notification routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.common import Notification

router = APIRouter()


@router.get("/notifikace", response_class=HTMLResponse)
def notifications_list(request: Request, db: Session = Depends(get_db)):
    """Show all notifications."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return request.app.state.templates.TemplateResponse(
        "notifications.html",
        {"request": request, "user": user, "notifications": notifs},
    )


@router.get("/notifikace/neprecetene", response_class=HTMLResponse)
def unread_dropdown(request: Request, db: Session = Depends(get_db)):
    """HTMX: dropdown of unread notifications."""
    user = get_current_user(request, db)
    if user is None:
        return HTMLResponse("")

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read == False)  # noqa: E712
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    return request.app.state.templates.TemplateResponse(
        "partials/notifications_dropdown.html",
        {"request": request, "notifications": notifs},
    )


@router.post("/notifikace/{notif_id}/precist")
def mark_read(notif_id: int, request: Request, db: Session = Depends(get_db)):
    """Mark a single notification as read."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    notif = db.query(Notification).filter(
        Notification.id == notif_id, Notification.user_id == user.id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()

    return RedirectResponse(url="/notifikace", status_code=303)


@router.post("/notifikace/precist-vse")
def mark_all_read(request: Request, db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False  # noqa: E712
    ).update({"is_read": True})
    db.commit()

    return RedirectResponse(url="/notifikace", status_code=303)
