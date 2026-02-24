"""Global search route."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.owner import Owner, Unit
from app.models.voting import Voting

router = APIRouter()


@router.get("/hledani", response_class=HTMLResponse)
def search(request: Request, q: str = "", db: Session = Depends(get_db)):
    """Full-text search across modules."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    results = {"owners": [], "units": [], "votings": []}

    if q and len(q) >= 2:
        term = f"%{q}%"

        # Search owners
        results["owners"] = (
            db.query(Owner)
            .filter(
                Owner.is_active == True,  # noqa: E712
                (Owner.first_name.ilike(term))
                | (Owner.last_name.ilike(term))
                | (Owner.email.ilike(term))
                | (Owner.birth_number.ilike(term))
                | (Owner.ico.ilike(term))
            )
            .limit(10)
            .all()
        )

        # Search units
        try:
            unit_num = int(q)
            results["units"] = (
                db.query(Unit).filter(Unit.unit_number == unit_num).limit(10).all()
            )
        except ValueError:
            results["units"] = (
                db.query(Unit)
                .filter(
                    (Unit.address.ilike(term)) | (Unit.building.ilike(term))
                )
                .limit(10)
                .all()
            )

        # Search votings
        results["votings"] = (
            db.query(Voting).filter(Voting.name.ilike(term)).limit(10).all()
        )

    total = sum(len(v) for v in results.values())

    return request.app.state.templates.TemplateResponse(
        request,
        "search.html",
        {"user": user, "q": q, "results": results, "total": total},
    )
