"""Authentication routes: login, logout, registration."""
from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, Request
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
        "login.html", {"request": request, "flash": flash}
    )


@router.post("/login")
def login_submit(request: Request, db: Session = Depends(get_db)):
    """Process login form."""
    import asyncio
    # We need to read form data synchronously in this sync endpoint
    # FastAPI allows sync route handlers
    from starlette.datastructures import FormData

    async def _get_form():
        return await request.form()

    loop = asyncio.new_event_loop()
    form = loop.run_until_complete(_get_form())
    loop.close()

    username = form.get("username", "")
    password = form.get("password", "")

    user = db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
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
        "register.html", {"request": request, "flash": flash}
    )


@router.post("/registrace")
def register_submit(request: Request, db: Session = Depends(get_db)):
    """Create first admin user."""
    import asyncio

    user_count = db.query(User).count()
    if user_count > 0:
        return RedirectResponse(url="/login", status_code=303)

    async def _get_form():
        return await request.form()

    loop = asyncio.new_event_loop()
    form = loop.run_until_complete(_get_form())
    loop.close()

    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    display_name = form.get("display_name", "").strip()

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
