"""Audit logging service."""
from sqlalchemy.orm import Session

from app.models.common import AuditLog


def log_change(
    db: Session,
    user_id: int | None,
    action: str,
    model_name: str,
    record_id: int | None,
    field_name: str = "",
    old_value: str = "",
    new_value: str = "",
) -> None:
    """Record a data change in the audit log."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        model_name=model_name,
        record_id=record_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    db.commit()
