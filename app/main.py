"""FastAPI application for SVJ Správa v2.0."""
import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.models import Base
from app.database import engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SVJ Správa", version="2.0")

# Session middleware for auth cookies
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Jinja2 templates with Czech locale filters
_template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_template_dir)


# --- Czech locale Jinja2 filters ---

def _format_datum(value) -> str:
    """Format date as DD.MM.YYYY."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y")
    return str(value)


def _format_cas(value) -> str:
    """Format datetime as HH:MM."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)


def _format_cislo(value) -> str:
    """Format number with Czech thousands separator (space) and decimal comma."""
    if value is None:
        return ""
    try:
        num = float(value)
        if num == int(num):
            # Integer: 1 234
            formatted = f"{int(num):,}".replace(",", "\u00a0")
        else:
            # Decimal: 1 234,56
            int_part = int(num)
            dec_part = f"{num:.2f}".split(".")[1]
            formatted = f"{int_part:,}".replace(",", "\u00a0") + "," + dec_part
        return formatted
    except (ValueError, TypeError):
        return str(value)


def _format_mena(value) -> str:
    """Format currency as Czech Kč."""
    return f"{_format_cislo(value)}\u00a0Kč"


templates.env.filters["datum"] = _format_datum
templates.env.filters["cas"] = _format_cas
templates.env.filters["cislo"] = _format_cislo
templates.env.filters["mena"] = _format_mena

# Store templates on app state for routers to access
app.state.templates = templates


# --- Middleware: inject user + flash + unread count into every template ---

from app.database import get_db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.common import Notification  # noqa: E402


@app.middleware("http")
async def inject_template_globals(request: Request, call_next):
    """Add user and notification count to template context."""
    response = await call_next(request)
    return response


# --- Include routers ---

from app.routers import auth as auth_router  # noqa: E402
from app.routers import dashboard as dashboard_router  # noqa: E402
from app.routers import search as search_router  # noqa: E402
from app.routers import notifications as notifications_router  # noqa: E402
from app.routers import owners as owners_router  # noqa: E402

app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(search_router.router)
app.include_router(notifications_router.router)
app.include_router(owners_router.router)

# Ensure data directories exist
for d in [settings.UPLOAD_DIR, settings.GENERATED_DIR, settings.BACKUP_DIR]:
    os.makedirs(d, exist_ok=True)
