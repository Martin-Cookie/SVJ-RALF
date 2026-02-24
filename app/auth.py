"""Authentication dependencies for FastAPI."""
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get the current authenticated user from session cookie."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
    return user


def require_login(request: Request, db: Session = Depends(get_db)) -> User:
    """Require an authenticated user. Redirects to login if not authenticated."""
    user = get_current_user(request, db)
    if user is None:
        from fastapi.responses import RedirectResponse
        raise HTTPException(status_code=303, detail="Not authenticated")
    return user


def require_role(*roles: str):
    """Dependency factory: require user to have one of the specified roles."""
    def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        user = get_current_user(request, db)
        if user is None:
            raise HTTPException(status_code=303, detail="Not authenticated")
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Nemáte oprávnění")
        return user
    return dependency
