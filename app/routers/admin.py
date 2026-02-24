"""Administration (Správa) routes."""
import csv
import glob
import io
import os
import shutil
import zipfile
from datetime import datetime
from typing import List, Optional

import bcrypt

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.administration import SvjInfo, SvjAddress, BoardMember
from app.models.common import AuditLog, EmailLog, ImportLog
from app.models.owner import Owner, Unit, OwnerUnit, Proxy
from app.models.user import User

# Backup directory
_BACKUP_DIR = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "backups")
os.makedirs(_BACKUP_DIR, exist_ok=True)

router = APIRouter()

_BACKUP_DIR_REAL = os.path.realpath(_BACKUP_DIR)


def _safe_backup_path(filename: str) -> Optional[str]:
    """Validate backup filename and return safe absolute path, or None if invalid."""
    # Only allow simple filenames: alphanumeric, dash, underscore, dot
    import re
    if not re.match(r'^[\w\-\.]+\.zip$', filename):
        return None
    fpath = os.path.realpath(os.path.join(_BACKUP_DIR, filename))
    if not fpath.startswith(_BACKUP_DIR_REAL + os.sep) and fpath != _BACKUP_DIR_REAL:
        return None
    return fpath


def _sanitize_backup_name(name: str) -> str:
    """Sanitize backup name to safe characters only."""
    import re
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return safe[:50] if safe else "backup"


def _require_admin(request: Request, db: Session):
    """Check that current user is admin. Returns user or raises 303/403."""
    user = get_current_user(request, db)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=303)
    if user.role != "admin":
        return user, HTMLResponse("Nemáte oprávnění", status_code=403)
    return user, None


@router.get("/sprava", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    """Show administration page."""
    user, err = _require_admin(request, db)
    if err:
        return err

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
    user, err = _require_admin(request, db)
    if err:
        return err

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
    user, err = _require_admin(request, db)
    if err:
        return err

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
    user, err = _require_admin(request, db)
    if err:
        return err

    member = db.query(BoardMember).filter(BoardMember.id == member_id).first()
    if member:
        db.delete(member)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Člen smazán."}

    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/clen/{member_id}/upravit")
def admin_edit_member(
    member_id: int,
    request: Request,
    name: str = Form(...),
    role: str = Form("Člen"),
    email: str = Form(""),
    phone: str = Form(""),
    db: Session = Depends(get_db),
):
    """Edit a board/control member."""
    user, err = _require_admin(request, db)
    if err:
        return err

    member = db.query(BoardMember).filter(BoardMember.id == member_id).first()
    if member is None:
        return HTMLResponse("Člen nenalezen", status_code=404)

    member.name = name
    member.role = role
    member.email = email
    member.phone = phone
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Člen aktualizován."}
    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/adresa/pridat")
def admin_add_address(
    request: Request,
    street: str = Form(""),
    city: str = Form(""),
    zip_code: str = Form(""),
    db: Session = Depends(get_db),
):
    """Add an SVJ address."""
    user, err = _require_admin(request, db)
    if err:
        return err

    addr = SvjAddress(street=street, city=city, zip_code=zip_code)
    db.add(addr)
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Adresa přidána."}
    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/adresa/{addr_id}/upravit")
def admin_edit_address(
    addr_id: int,
    request: Request,
    street: str = Form(""),
    city: str = Form(""),
    zip_code: str = Form(""),
    db: Session = Depends(get_db),
):
    """Edit an SVJ address."""
    user, err = _require_admin(request, db)
    if err:
        return err

    addr = db.query(SvjAddress).filter(SvjAddress.id == addr_id).first()
    if addr is None:
        return HTMLResponse("Adresa nenalezena", status_code=404)

    addr.street = street
    addr.city = city
    addr.zip_code = zip_code
    db.commit()

    request.session["flash"] = {"type": "success", "message": "Adresa aktualizována."}
    return RedirectResponse(url="/sprava", status_code=303)


@router.post("/sprava/adresa/{addr_id}/smazat")
def admin_delete_address(
    addr_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete an SVJ address."""
    user, err = _require_admin(request, db)
    if err:
        return err

    addr = db.query(SvjAddress).filter(SvjAddress.id == addr_id).first()
    if addr:
        db.delete(addr)
        db.commit()
        request.session["flash"] = {"type": "success", "message": "Adresa smazána."}

    return RedirectResponse(url="/sprava", status_code=303)


# --- User Management ---


@router.get("/sprava/uzivatele", response_class=HTMLResponse)
def user_list(request: Request, db: Session = Depends(get_db)):
    """List all users (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    users = db.query(User).order_by(User.created_at.desc()).all()

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/uzivatele.html",
        {"user": user, "users": users},
    )


@router.post("/sprava/uzivatele/novy")
def user_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
    role: str = Form("reader"),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    # Validate
    if len(password) < 6:
        request.session["flash"] = {"type": "error", "message": "Heslo musí mít alespoň 6 znaků."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        request.session["flash"] = {"type": "error", "message": f"Uživatel '{username}' již existuje."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    if role not in ("admin", "editor", "reader"):
        role = "reader"

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_user = User(
        username=username,
        password_hash=pw_hash,
        role=role,
        display_name=display_name or username,
        is_active=True,
    )
    db.add(new_user)
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Uživatel '{username}' vytvořen."}
    return RedirectResponse(url="/sprava/uzivatele", status_code=303)


@router.post("/sprava/uzivatele/{user_id}/role")
def user_change_role(
    user_id: int,
    request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    """Change user role (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        request.session["flash"] = {"type": "error", "message": "Uživatel nenalezen."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    if role not in ("admin", "editor", "reader"):
        role = "reader"

    # Prevent demoting last admin
    if target.role == "admin" and role != "admin":
        admin_count = db.query(User).filter(
            User.role == "admin", User.is_active == True  # noqa: E712
        ).count()
        if admin_count <= 1:
            request.session["flash"] = {"type": "error", "message": "Nelze změnit roli posledního administrátora."}
            return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    target.role = role
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Role uživatele '{target.username}' změněna na '{role}'."}
    return RedirectResponse(url="/sprava/uzivatele", status_code=303)


@router.post("/sprava/uzivatele/{user_id}/heslo")
def user_reset_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Reset user password (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        request.session["flash"] = {"type": "error", "message": "Uživatel nenalezen."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    if len(password) < 6:
        request.session["flash"] = {"type": "error", "message": "Heslo musí mít alespoň 6 znaků."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    target.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.commit()

    request.session["flash"] = {"type": "success", "message": f"Heslo uživatele '{target.username}' změněno."}
    return RedirectResponse(url="/sprava/uzivatele", status_code=303)


@router.post("/sprava/uzivatele/{user_id}/stav")
def user_toggle_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Activate/deactivate user (admin only). Admin cannot deactivate themselves."""
    user, err = _require_admin(request, db)
    if err:
        return err

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        request.session["flash"] = {"type": "error", "message": "Uživatel nenalezen."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    # Prevent self-deactivation
    if target.id == user.id:
        request.session["flash"] = {"type": "error", "message": "Nemůžete deaktivovat sami sebe."}
        return RedirectResponse(url="/sprava/uzivatele", status_code=303)

    target.is_active = not target.is_active
    db.commit()

    action = "aktivován" if target.is_active else "deaktivován"
    request.session["flash"] = {"type": "success", "message": f"Uživatel '{target.username}' {action}."}
    return RedirectResponse(url="/sprava/uzivatele", status_code=303)


# --- Audit Log ---


@router.get("/sprava/audit", response_class=HTMLResponse)
def audit_log_page(
    request: Request,
    action: str = "",
    model: str = "",
    db: Session = Depends(get_db),
):
    """View audit log (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())

    if action:
        query = query.filter(AuditLog.action == action)
    if model:
        query = query.filter(AuditLog.model_name == model)

    logs = query.limit(200).all()

    # Get distinct actions and models for filters
    actions = [r[0] for r in db.query(AuditLog.action).distinct().all() if r[0]]
    models = [r[0] for r in db.query(AuditLog.model_name).distinct().all() if r[0]]

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/audit.html",
        {
            "user": user,
            "logs": logs,
            "actions": actions,
            "models": models,
            "current_action": action,
            "current_model": model,
        },
    )


# --- Backup & Restore ---


@router.get("/sprava/zalohy", response_class=HTMLResponse)
def backup_list(request: Request, db: Session = Depends(get_db)):
    """List backups (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    backups = []
    if os.path.exists(_BACKUP_DIR):
        for f in sorted(os.listdir(_BACKUP_DIR), reverse=True):
            if f.endswith(".zip"):
                fpath = os.path.join(_BACKUP_DIR, f)
                size = os.path.getsize(fpath)
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                backups.append({"filename": f, "size": size, "date": mtime})

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/zalohy.html",
        {"user": user, "backups": backups},
    )


@router.post("/sprava/zaloha/vytvorit")
def backup_create(
    request: Request,
    name: str = Form(""),
    db: Session = Depends(get_db),
):
    """Create a ZIP backup of database + uploads (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = _sanitize_backup_name(name) if name else "backup"
    zip_name = f"{label}_{timestamp}.zip"
    zip_path = os.path.join(_BACKUP_DIR, zip_name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add database file
            db_path = settings.DATABASE_PATH
            if os.path.exists(db_path):
                zf.write(db_path, "svj.db")

            # Add uploads
            upload_dir = settings.UPLOAD_DIR
            if os.path.exists(upload_dir):
                for root, dirs, files in os.walk(upload_dir):
                    # Skip temp import files
                    if "_import_temp" in root:
                        continue
                    for f in files:
                        fpath = os.path.join(root, f)
                        arcname = os.path.join("uploads", os.path.relpath(fpath, upload_dir))
                        zf.write(fpath, arcname)

        request.session["flash"] = {"type": "success", "message": f"Záloha '{zip_name}' vytvořena."}
    except Exception as e:
        request.session["flash"] = {"type": "error", "message": f"Chyba při vytváření zálohy: {e}"}

    return RedirectResponse(url="/sprava/zalohy", status_code=303)


@router.get("/sprava/zaloha/{filename}/stahnout")
def backup_download(filename: str, request: Request, db: Session = Depends(get_db)):
    """Download a backup file (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    fpath = _safe_backup_path(filename)
    if not fpath or not os.path.exists(fpath):
        request.session["flash"] = {"type": "error", "message": "Záloha nenalezena."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    def iterfile():
        with open(fpath, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(fpath)}"},
    )


@router.post("/sprava/zaloha/{filename}/smazat")
def backup_delete(filename: str, request: Request, db: Session = Depends(get_db)):
    """Delete a backup file (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    fpath = _safe_backup_path(filename)
    if fpath and os.path.exists(fpath):
        os.remove(fpath)
        request.session["flash"] = {"type": "success", "message": f"Záloha '{filename}' smazána."}
    else:
        request.session["flash"] = {"type": "error", "message": "Záloha nenalezena."}

    return RedirectResponse(url="/sprava/zalohy", status_code=303)


@router.post("/sprava/zaloha/obnovit")
def backup_restore(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Restore from uploaded ZIP backup (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    if not file.filename or not file.filename.endswith(".zip"):
        request.session["flash"] = {"type": "error", "message": "Nahrajte ZIP soubor se zálohou."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    # Save uploaded ZIP
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            # Check it contains svj.db
            if "svj.db" not in zf.namelist():
                request.session["flash"] = {"type": "error", "message": "ZIP neobsahuje svj.db."}
                return RedirectResponse(url="/sprava/zalohy", status_code=303)

            # Create safety backup first
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_path = os.path.join(_BACKUP_DIR, f"pre_restore_{timestamp}.zip")
            with zipfile.ZipFile(safety_path, "w") as safety:
                db_path = settings.DATABASE_PATH
                if os.path.exists(db_path):
                    safety.write(db_path, "svj.db")

            # Extract DB
            db_path = settings.DATABASE_PATH
            zf.extract("svj.db", os.path.dirname(db_path))

            # Extract uploads if present (Zip Slip protection)
            upload_parent = os.path.realpath(os.path.dirname(settings.UPLOAD_DIR))
            for name in zf.namelist():
                if name.startswith("uploads/"):
                    target = os.path.realpath(os.path.join(upload_parent, name))
                    if not target.startswith(upload_parent + os.sep):
                        continue  # Skip path traversal attempts
                    zf.extract(name, upload_parent)

        request.session["flash"] = {"type": "success", "message": "Obnova dokončena. Restartujte aplikaci."}
    except Exception as e:
        request.session["flash"] = {"type": "error", "message": f"Chyba obnovy: {e}"}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return RedirectResponse(url="/sprava/zalohy", status_code=303)


@router.post("/sprava/zaloha/obnovit-soubor")
async def backup_restore_db_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Restore from uploaded .db file (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    filename = file.filename or ""
    if not filename.endswith(".db"):
        request.session["flash"] = {"type": "error", "message": "Nahrajte soubor .db (SQLite databázi)."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    # Read with size limit (500 MB)
    _MAX_DB_SIZE = 500 * 1024 * 1024
    content = await file.read(_MAX_DB_SIZE + 1)
    if len(content) > _MAX_DB_SIZE:
        request.session["flash"] = {"type": "error", "message": "Soubor je příliš velký (max 500 MB)."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    # Validate it's a real SQLite file (magic bytes: "SQLite format 3\000")
    if not content.startswith(b"SQLite format 3\x00"):
        request.session["flash"] = {"type": "error", "message": "Neplatný soubor — není SQLite databáze."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    try:
        # Create safety backup first
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = os.path.join(_BACKUP_DIR, f"pre_restore_{timestamp}.zip")
        with zipfile.ZipFile(safety_path, "w") as safety:
            db_path = settings.DATABASE_PATH
            if os.path.exists(db_path):
                safety.write(db_path, "svj.db")

        # Replace DB file
        db_path = settings.DATABASE_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with open(db_path, "wb") as f:
            f.write(content)

        request.session["flash"] = {"type": "success", "message": "Obnova z .db souboru dokončena. Restartujte aplikaci."}
    except Exception as e:
        request.session["flash"] = {"type": "error", "message": f"Chyba obnovy: {e}"}

    return RedirectResponse(url="/sprava/zalohy", status_code=303)


# --- Data Deletion (Danger Zone) ---


def _get_delete_models(cat: str):
    """Return list of model classes for a category (lazy imports for some)."""
    if cat == "owners":
        return [OwnerUnit, Proxy, Unit, Owner]
    elif cat == "voting":
        from app.models.voting import BallotVote, Ballot, VotingItem, Voting
        return [BallotVote, Ballot, VotingItem, Voting]
    elif cat == "tax":
        from app.models.tax import TaxDistribution, TaxDocument, TaxSession
        return [TaxDistribution, TaxDocument, TaxSession]
    elif cat == "sync":
        from app.models.sync import SyncSession
        return [SyncSession]
    elif cat == "logs":
        return [AuditLog, EmailLog, ImportLog]
    elif cat == "admin":
        return [BoardMember, SvjAddress, SvjInfo]
    return []


_DELETE_CATEGORIES = {
    "owners": "Vlastníci a jednotky",
    "voting": "Hlasování",
    "tax": "Daně",
    "sync": "Synchronizace",
    "logs": "Logy",
    "admin": "Administrace",
}


@router.get("/sprava/smazat-data", response_class=HTMLResponse)
def delete_data_page(request: Request, db: Session = Depends(get_db)):
    """Show danger zone — data deletion page (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    categories = []
    for key, label in _DELETE_CATEGORIES.items():
        models = _get_delete_models(key)
        count = sum(db.query(m).count() for m in models)
        categories.append({"key": key, "label": label, "count": count})

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/smazat_data.html",
        {"user": user, "categories": categories},
    )


@router.post("/sprava/smazat-data")
async def delete_data_execute(request: Request, db: Session = Depends(get_db)):
    """Execute data deletion (admin only). Requires confirmation=DELETE."""
    user, err = _require_admin(request, db)
    if err:
        return err

    form = await request.form()
    confirmation = form.get("confirmation", "")
    categories = form.getlist("categories")

    if confirmation != "DELETE":
        request.session["flash"] = {"type": "error", "message": "Pro smazání zadejte slovo DELETE."}
        return RedirectResponse(url="/sprava/smazat-data", status_code=303)

    if not categories:
        request.session["flash"] = {"type": "error", "message": "Vyberte alespoň jednu kategorii."}
        return RedirectResponse(url="/sprava/smazat-data", status_code=303)

    # Create safety backup before mass delete
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = os.path.join(_BACKUP_DIR, f"pre_delete_{timestamp}.zip")
        with zipfile.ZipFile(safety_path, "w") as safety:
            db_path = settings.DATABASE_PATH
            if os.path.exists(db_path):
                safety.write(db_path, "svj.db")
    except Exception:
        pass  # Best effort safety backup

    total = 0
    for cat in categories:
        models = _get_delete_models(cat)
        for model in models:
            count = db.query(model).delete()
            total += count

    # Audit log entry for mass deletion
    audit = AuditLog(
        user_id=user.id,
        action="delete",
        model_name="MassDelete",
        field_name=",".join(categories),
        new_value=f"{total} records deleted",
    )
    db.add(audit)
    db.commit()
    request.session["flash"] = {"type": "success", "message": f"Smazáno {total} záznamů."}
    return RedirectResponse(url="/sprava/smazat-data", status_code=303)


# --- Data Export ---


def _export_model_to_rows(db: Session, model, columns: list):
    """Export model data as list of dicts."""
    rows = []
    for obj in db.query(model).all():
        row = {}
        for col in columns:
            val = getattr(obj, col, "")
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d %H:%M:%S")
            elif val is None:
                val = ""
            row[col] = val
        rows.append(row)
    return rows


def _get_export_data(db: Session, cat: str):
    """Return (filename, columns, rows) for a category."""
    if cat == "owners":
        cols = ["id", "first_name", "last_name", "owner_type", "email", "phone",
                "address", "data_box", "bank_account"]
        return "vlastnici", cols, _export_model_to_rows(db, Owner, cols)
    elif cat == "units":
        cols = ["id", "unit_number", "building_number", "space_type", "section",
                "floor_area", "room_count", "address", "orientation_number", "lv_number"]
        return "jednotky", cols, _export_model_to_rows(db, Unit, cols)
    elif cat == "logs":
        cols = ["id", "action", "model_name", "record_id", "field_name", "old_value", "new_value"]
        return "audit_log", cols, _export_model_to_rows(db, AuditLog, cols)
    return cat, [], []


def _rows_to_xlsx(filename: str, columns: list, rows: list) -> bytes:
    """Convert rows to xlsx bytes."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = filename
    ws.append(columns)
    for row in rows:
        ws.append([row.get(c, "") for c in columns])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _rows_to_csv(columns: list, rows: list) -> bytes:
    """Convert rows to CSV bytes (UTF-8 with BOM)."""
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


@router.get("/sprava/export", response_class=HTMLResponse)
def export_page(request: Request, db: Session = Depends(get_db)):
    """Show export page (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    export_categories = [
        {"key": "owners", "label": "Vlastníci"},
        {"key": "units", "label": "Jednotky"},
        {"key": "logs", "label": "Audit log"},
    ]

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/export.html",
        {"user": user, "export_categories": export_categories},
    )


@router.post("/sprava/export")
async def export_execute(request: Request, db: Session = Depends(get_db)):
    """Execute data export (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    form = await request.form()
    categories = form.getlist("categories")
    fmt = form.get("format", "xlsx")

    if not categories:
        request.session["flash"] = {"type": "error", "message": "Vyberte alespoň jednu kategorii."}
        return RedirectResponse(url="/sprava/export", status_code=303)

    exports = []
    for cat in categories:
        filename, columns, rows = _get_export_data(db, cat)
        if not columns:
            continue
        if fmt == "csv":
            data = _rows_to_csv(columns, rows)
            ext = "csv"
        else:
            data = _rows_to_xlsx(filename, columns, rows)
            ext = "xlsx"
        exports.append((f"{filename}.{ext}", data))

    if len(exports) == 0:
        request.session["flash"] = {"type": "error", "message": "Žádná data k exportu."}
        return RedirectResponse(url="/sprava/export", status_code=303)

    if len(exports) == 1:
        fname, data = exports[0]
        if fmt == "csv":
            media = "text/csv; charset=utf-8"
        else:
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return Response(
            content=data,
            media_type=media,
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )

    # Multiple → ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, data in exports:
            zf.writestr(fname, data)
    buf.seek(0)

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=export.zip"},
    )


# --- Bulk Edits ---

_BULK_EDIT_FIELDS = {
    "space_type": {"label": "Typ prostoru", "column": "space_type"},
    "section": {"label": "Sekce", "column": "section"},
    "room_count": {"label": "Počet místností", "column": "room_count"},
    "ownership_type": {"label": "Druh vlastnictví", "column": "ownership_type"},
    "address": {"label": "Adresa", "column": "address"},
    "orientation_number": {"label": "Orientační číslo", "column": "orientation_number"},
}


@router.get("/sprava/hromadne-upravy", response_class=HTMLResponse)
def bulk_edits_page(
    request: Request,
    field: str = "",
    db: Session = Depends(get_db),
):
    """Show bulk edits page (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    fields = [{"key": k, "label": v["label"]} for k, v in _BULK_EDIT_FIELDS.items()]
    values = []
    selected_field = field

    if field and field in _BULK_EDIT_FIELDS:
        col_name = _BULK_EDIT_FIELDS[field]["column"]
        from sqlalchemy import func

        if field == "ownership_type":
            col = getattr(OwnerUnit, col_name)
            results = (
                db.query(col, func.count(OwnerUnit.id))
                .group_by(col)
                .order_by(func.count(OwnerUnit.id).desc())
                .all()
            )
        else:
            col = getattr(Unit, col_name)
            results = (
                db.query(col, func.count(Unit.id))
                .group_by(col)
                .order_by(func.count(Unit.id).desc())
                .all()
            )

        for val, cnt in results:
            values.append({"value": val or "(prázdné)", "count": cnt, "raw": val or ""})

    return request.app.state.templates.TemplateResponse(
        request,
        "admin/hromadne_upravy.html",
        {
            "user": user,
            "fields": fields,
            "values": values,
            "selected_field": selected_field,
        },
    )


@router.post("/sprava/hromadne-upravy")
async def bulk_edits_apply(request: Request, db: Session = Depends(get_db)):
    """Apply bulk edit (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    form = await request.form()
    field = form.get("field", "")
    old_value = form.get("old_value", "")
    new_value = form.get("new_value", "")
    unit_ids = form.getlist("unit_ids")

    if not field or field not in _BULK_EDIT_FIELDS or not new_value:
        request.session["flash"] = {"type": "error", "message": "Chybné parametry."}
        return RedirectResponse(url="/sprava/hromadne-upravy", status_code=303)

    col_name = _BULK_EDIT_FIELDS[field]["column"]
    updated = 0

    if field == "ownership_type":
        query = db.query(OwnerUnit)
        if unit_ids:
            query = query.filter(OwnerUnit.id.in_([int(x) for x in unit_ids]))
        if old_value:
            query = query.filter(getattr(OwnerUnit, col_name) == old_value)
        updated = query.update({col_name: new_value}, synchronize_session="fetch")
    else:
        query = db.query(Unit)
        if unit_ids:
            query = query.filter(Unit.id.in_([int(x) for x in unit_ids]))
        if old_value:
            query = query.filter(getattr(Unit, col_name) == old_value)
        updated = query.update({col_name: new_value}, synchronize_session="fetch")

    # Audit log for bulk edit
    audit = AuditLog(
        user_id=user.id,
        action="update",
        model_name="BulkEdit",
        field_name=col_name,
        old_value=old_value,
        new_value=f"{new_value} ({updated} records)",
    )
    db.add(audit)
    db.commit()

    label = _BULK_EDIT_FIELDS[field]["label"]
    request.session["flash"] = {
        "type": "success",
        "message": f"Aktualizováno {updated} záznamů ({label}: '{old_value}' → '{new_value}').",
    }
    return RedirectResponse(url=f"/sprava/hromadne-upravy?field={field}", status_code=303)
