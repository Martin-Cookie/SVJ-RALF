"""Authentication routes: login, logout, registration."""
from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    """Show login form. Redirect to register if no users exist."""
    user_count = db.query(User).count()
    if user_count == 0:
        return RedirectResponse(url="/registrace", status_code=303)

    # If already logged in, go to dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)

    flash = request.session.pop("flash", None)
    return request.app.state.templates.TemplateResponse(
        request, "login.html", {"flash": flash}
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    """Process login form."""
    user = db.query(User).filter(
        User.username == username, User.is_active == True  # noqa: E712
    ).first()
    if user and bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        request.session["user_id"] = user.id
        user.last_login = datetime.utcnow()
        db.commit()
        return RedirectResponse(url="/", status_code=303)

    request.session["flash"] = {"type": "error", "message": "Nesprávné přihlašovací údaje."}
    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/registrace", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    """Show registration form. Only available when no users exist."""
    user_count = db.query(User).count()
    if user_count > 0:
        return RedirectResponse(url="/login", status_code=303)

    flash = request.session.pop("flash", None)
    return request.app.state.templates.TemplateResponse(
        request, "register.html", {"flash": flash}
    )


@router.post("/registrace")
def register_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    display_name: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create first admin user."""
    user_count = db.query(User).count()
    if user_count > 0:
        return RedirectResponse(url="/login", status_code=303)

    username = username.strip()
    password = password.strip()
    display_name = display_name.strip()

    if not username or not password:
        request.session["flash"] = {"type": "error", "message": "Vyplňte všechna povinná pole."}
        return RedirectResponse(url="/registrace", status_code=303)

    if len(password) < 6:
        request.session["flash"] = {"type": "error", "message": "Heslo musí mít alespoň 6 znaků."}
        return RedirectResponse(url="/registrace", status_code=303)

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=username,
        password_hash=pw_hash,
        role="admin",
        display_name=display_name or username,
        is_active=True,
    )
    db.add(user)
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)
