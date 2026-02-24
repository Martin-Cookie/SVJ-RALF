"""Voting management routes."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
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
async def voting_create(
    request: Request,
    name: str = Form(...),
    quorum: float = Form(50.0),
    start_date: str = Form(""),
    end_date: str = Form(""),
    template: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a new voting, optionally with a .docx template."""
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
    db.flush()  # Get the ID before saving template

    # Handle template upload
    if template and template.filename and template.filename.endswith(".docx"):
        upload_dir = os.path.join(settings.UPLOAD_DIR, "templates")
        os.makedirs(upload_dir, exist_ok=True)
        template_file = os.path.join(upload_dir, f"voting-{v.id}.docx")
        content = await template.read()
        with open(template_file, "wb") as f:
            f.write(content)
        v.template_path = template_file

        # Parse items from template
        try:
            from app.services.word_parser import parse_voting_items

            items = parse_voting_items(template_file)
            for i, text in enumerate(items, 1):
                db.add(VotingItem(voting_id=v.id, number=i, text=text))
        except Exception:
            pass  # Template parsing is best-effort; items can be added manually

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


@router.post("/hlasovani/{voting_id}/generovat")
def voting_generate_ballots(
    voting_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate ballot documents for all owners with units."""
    from app.models.owner import Owner, OwnerUnit

    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None:
        return HTMLResponse("Hlasování nenalezeno", status_code=404)
    if voting.status != "koncept":
        request.session["flash"] = {"type": "error", "message": "Lístky lze generovat pouze v konceptu."}
        return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)

    items = (
        db.query(VotingItem)
        .filter(VotingItem.voting_id == voting_id)
        .order_by(VotingItem.number)
        .all()
    )
    if not items:
        request.session["flash"] = {"type": "error", "message": "Hlasování nemá žádné body."}
        return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)

    # Find owners with active units
    active_owners = (
        db.query(Owner)
        .join(OwnerUnit, Owner.id == OwnerUnit.owner_id)
        .filter(OwnerUnit.valid_to.is_(None))
        .distinct()
        .all()
    )

    if not active_owners:
        request.session["flash"] = {"type": "error", "message": "Žádní vlastníci s aktivními jednotkami."}
        return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)

    item_texts = [item.text for item in items]
    generated = 0

    from app.models.owner import Unit
    from app.services.pdf_generator import generate_ballot_pdf

    for owner in active_owners:
        # Get owner's active units
        owner_units = (
            db.query(OwnerUnit)
            .filter(OwnerUnit.owner_id == owner.id, OwnerUnit.valid_to.is_(None))
            .all()
        )
        unit_ids = [ou.unit_id for ou in owner_units]
        units = db.query(Unit).filter(Unit.id.in_(unit_ids)).all()
        unit_numbers = ", ".join(str(u.unit_number) for u in units)

        # Generate document
        output_dir = os.path.join(settings.GENERATED_DIR, f"voting-{voting_id}")
        output_path = os.path.join(output_dir, f"ballot-{voting_id}-{owner.id}.docx")

        generate_ballot_pdf(
            template_path=voting.template_path or "",
            output_path=output_path,
            voting_name=voting.name,
            owner_name=owner.display_name,
            unit_numbers=unit_numbers,
            items=item_texts,
        )

        # Create ballot record for first unit
        ballot = Ballot(
            voting_id=voting_id,
            owner_id=owner.id,
            unit_id=units[0].id if units else None,
            status="vygenerován",
            pdf_path=output_path,
        )
        db.add(ballot)
        generated += 1

    voting.status = "aktivní"
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Vygenerováno {generated} lístků. Hlasování aktivováno."}
    return RedirectResponse(url=f"/hlasovani/{voting_id}", status_code=303)


@router.get("/hlasovani/{voting_id}/listky", response_class=HTMLResponse)
def voting_ballots_list(
    voting_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """List ballots for a voting."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)

    voting = db.query(Voting).filter(Voting.id == voting_id).first()
    if voting is None:
        return HTMLResponse("Hlasování nenalezeno", status_code=404)

    ballots = (
        db.query(Ballot)
        .filter(Ballot.voting_id == voting_id)
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        request,
        "voting/ballots.html",
        {
            "user": user,
            "voting": voting,
            "ballots": ballots,
        },
    )


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
