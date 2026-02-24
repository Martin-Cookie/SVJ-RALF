"""Dashboard route."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.owner import Owner, Unit
from app.models.voting import Voting
from app.models.user import User

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard with overview statistics."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    owner_count = db.query(Owner).filter(Owner.is_active == True).count()  # noqa: E712
    unit_count = db.query(Unit).count()
    voting_active = db.query(Voting).filter(Voting.status == "aktivní").count()
    voting_draft = db.query(Voting).filter(Voting.status == "koncept").count()

    # Active/draft votings for dashboard cards
    active_votings = db.query(Voting).filter(
        Voting.status.in_(["aktivní", "koncept"])
    ).order_by(Voting.created_at.desc()).limit(5).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "owner_count": owner_count,
            "unit_count": unit_count,
            "voting_active": voting_active,
            "voting_draft": voting_draft,
            "active_votings": active_votings,
        },
    )
