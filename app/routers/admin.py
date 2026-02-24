"""Administration (Správa) routes."""
import glob
import os
import shutil
import zipfile
from datetime import datetime

import bcrypt

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.administration import SvjInfo, SvjAddress, BoardMember
from app.models.common import AuditLog
from app.models.user import User

# Backup directory
_BACKUP_DIR = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "backups")
os.makedirs(_BACKUP_DIR, exist_ok=True)

router = APIRouter()


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
    label = name.replace(" ", "_") if name else "backup"
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

    fpath = os.path.join(_BACKUP_DIR, filename)
    if not os.path.exists(fpath) or not filename.endswith(".zip"):
        request.session["flash"] = {"type": "error", "message": "Záloha nenalezena."}
        return RedirectResponse(url="/sprava/zalohy", status_code=303)

    def iterfile():
        with open(fpath, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/sprava/zaloha/{filename}/smazat")
def backup_delete(filename: str, request: Request, db: Session = Depends(get_db)):
    """Delete a backup file (admin only)."""
    user, err = _require_admin(request, db)
    if err:
        return err

    fpath = os.path.join(_BACKUP_DIR, filename)
    if os.path.exists(fpath) and filename.endswith(".zip"):
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

            # Extract uploads if present
            for name in zf.namelist():
                if name.startswith("uploads/"):
                    zf.extract(name, os.path.dirname(settings.UPLOAD_DIR))

        request.session["flash"] = {"type": "success", "message": "Obnova dokončena. Restartujte aplikaci."}
    except Exception as e:
        request.session["flash"] = {"type": "error", "message": f"Chyba obnovy: {e}"}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return RedirectResponse(url="/sprava/zalohy", status_code=303)
