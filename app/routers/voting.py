"""Voting management routes."""
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.voting import Voting, VotingItem, Ballot, BallotVote

router = APIRouter()


@router.get("/hlasovani", response_class=HTMLResponse)
def voting_list(
    request: Request,
    status: str = "",
    db: Session = Depends(get_db),
):
    """List all votings with status filter."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    query = db.query(Voting)
    if status:
        query = query.filter(Voting.status == status)
    query = query.order_by(Voting.created_at.desc())
    votings = query.all()

    # Count by status for filter bubbles
    total = db.query(Voting).count()
    koncept_count = db.query(Voting).filter(Voting.status == "koncept").count()
    aktivni_count = db.query(Voting).filter(Voting.status == "aktivní").count()
    uzavrene_count = db.query(Voting).filter(Voting.status == "uzavřené").count()
    zrusene_count = db.query(Voting).filter(Voting.status == "zrušené").count()

    return request.app.state.templates.TemplateResponse(
        request,
        "voting/list.html",
        {
            "user": user,
            "votings": votings,
            "status": status,
            "total": total,
            "koncept_count": koncept_count,
            "aktivni_count": aktivni_count,
            "uzavrene_count": uzavrene_count,
            "zrusene_count": zrusene_count,
        },
    )


@router.get("/hlasovani/nova", response_class=HTMLResponse)
def voting_create_page(request: Request, db: Session = Depends(get_db)):
    """Show new voting creation form."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    return request.app.state.templates.TemplateResponse(
        request, "voting/create.html", {"user": user}
    )


@router.post("/hlasovani/nova")
def voting_create(
    request: Request,
    name: str = Form(...),
    quorum: float = Form(50.0),
    start_date: str = Form(""),
    end_date: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a new voting."""
    from datetime import date

    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    v = Voting(name=name, quorum=quorum, status="koncept")

    if start_date:
        try:
            v.start_date = date.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            v.end_date = date.fromisoformat(end_date)
        except ValueError:
            pass

    db.add(v)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Hlasování '{name}' vytvořeno."}
    return RedirectResponse(url=f"/hlasovani/{v.id}", status_code=303)


@router.get("/hlasovani/{voting_id}", response_class=HTMLResponse)
def voting_detail(
    voting_id: int, request: Request, db: Session = Depends(get_db)
):
    """Show voting detail with items and results."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None:
        return HTMLResponse("Hlasování nenalezeno", status_code=404)

    items = (
        db.query(VotingItem)
        .filter(VotingItem.voting_id == voting_id)
        .order_by(VotingItem.number)
        .all()
    )

    # Calculate results per item
    results = []
    for item in items:
        votes = (
            db.query(BallotVote)
            .filter(BallotVote.voting_item_id == item.id)
            .all()
        )
        pro = sum(1 for v in votes if v.vote == "PRO")
        proti = sum(1 for v in votes if v.vote == "PROTI")
        zdrzel = sum(1 for v in votes if v.vote == "Zdržel se")
        total_votes = pro + proti + zdrzel
        results.append({
            "item": item,
            "pro": pro,
            "proti": proti,
            "zdrzel": zdrzel,
            "total": total_votes,
            "pro_pct": round(pro / total_votes * 100, 1) if total_votes > 0 else 0,
            "proti_pct": round(proti / total_votes * 100, 1) if total_votes > 0 else 0,
            "zdrzel_pct": round(zdrzel / total_votes * 100, 1) if total_votes > 0 else 0,
        })

    ballot_count = db.query(Ballot).filter(Ballot.voting_id == voting_id).count()
    processed_count = (
        db.query(Ballot)
        .filter(Ballot.voting_id == voting_id, Ballot.status == "zpracován")
        .count()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "voting/detail.html",
        {
            "user": user,
            "voting": voting,
            "items": items,
            "results": results,
            "ballot_count": ballot_count,
            "processed_count": processed_count,
        },
    )


@router.post("/hlasovani/{voting_id}/pridat-bod")
def voting_add_item(
    voting_id: int,
    request: Request,
    text: str = Form(...),
    db: Session = Depends(get_db),
):
    """Add an item to a voting (only in koncept state)."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None:
        return HTMLResponse("Hlasování nenalezeno", status_code=404)
    if voting.status != "koncept":
        request.session["flash"] = {"type": "error", "message": "Body lze přidávat pouze v konceptu."}
        return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)

    # Get next number
    max_num = (
        db.query(VotingItem.number)
        .filter(VotingItem.voting_id == voting_id)
        .order_by(VotingItem.number.desc())
        .first()
    )
    next_num = (max_num[0] + 1) if max_num else 1

    item = VotingItem(voting_id=voting_id, number=next_num, text=text)
    db.add(item)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Bod {next_num} přidán."}
    return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)


@router.post("/hlasovani/{voting_id}/smazat-bod/{item_id}")
def voting_delete_item(
    voting_id: int,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete an item from a voting (only in koncept state)."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None or voting.status != "koncept":
        return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)

    item = db.query(VotingItem).filter(
        VotingItem.id == item_id, VotingItem.voting_id == voting_id
    ).first()
    if item:
        db.delete(item)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Bod smazán."}

    return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)


@router.post("/hlasovani/{voting_id}/stav")
def voting_change_status(
    voting_id: int,
    request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    """Change voting status."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None:
        return HTMLResponse("Hlasování nenalezeno", status_code=404)

    valid_transitions = {
        "koncept": ["aktivní", "zrušené"],
        "aktivní": ["uzavřené", "zrušené"],
        "uzavřené": [],
        "zrušené": [],
    }

    if status in valid_transitions.get(voting.status, []):
        voting.status = status
        db.commit()
        request.session["flash"] = {"type": "success", "message": f"Stav změněn na '{status}'."}
    else:
        request.session["flash"] = {"type": "error", "message": f"Nelze změnit stav z '{voting.status}' na '{status}'."}

    return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)


@router.post("/hlasovani/{voting_id}/smazat")
def voting_delete(
    voting_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a voting with cascade."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting:
        db.delete(voting)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Hlasování smazáno."}

    return RedirectResponse(url="/hlasovani", status_code=303)
