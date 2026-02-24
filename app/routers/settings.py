"""Settings (Nastavení) routes."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

router = APIRouter()


@router.get("/nastaveni", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    """Show settings page."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    return request.app.state.templates.TemplateResponse(
        request,
        "settings/index.html",
        {"user": user},
    )
