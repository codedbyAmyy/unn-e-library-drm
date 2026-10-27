"""Administrator in-app announcement management (no email delivery)."""
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/admin/notifications", tags=["Administration Notifications"])
Database = Annotated[Session, Depends(get_db)]
Administrator = Annotated[User, Depends(require_roles("admin"))]
Role = Literal["student", "lecturer", "librarian", "admin"]


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5, max_length=2000)
    audience: Literal["all", "student", "lecturer", "librarian", "admin"]


@router.get("/overview")
def overview(db: Database, admin: Administrator):
    total = db.scalar(select(func.count(Notification.id))) or 0
    unread = db.scalar(select(func.count(Notification.id)).where(Notification.is_read.is_(False))) or 0
    active = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    groups = dict(db.execute(select(Notification.notification_type, func.count(Notification.id)).group_by(Notification.notification_type)).all())
    return {"total_records": total, "unread_records": unread, "active_users": active, "by_type": groups}


@router.get("/records")
def records(
    db: Database,
    admin: Administrator,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    notification_type: Literal["general", "system", "new_resource", "resource_request", "course_reading_list"] | None = None,
):
    filters = [Notification.notification_type == notification_type] if notification_type else []
    count = db.scalar(select(func.count(Notification.id)).where(*filters)) or 0
    entries = db.execute(
        select(Notification, User.full_name, User.role)
        .join(User, User.id == Notification.user_id)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {"total": count, "items": [
        {"id": n.id, "title": n.title, "notification_type": n.notification_type,
         "recipient_name": name, "recipient_role": role, "is_read": n.is_read,
         "created_at": n.created_at.isoformat() if n.created_at else None}
        for n, name, role in entries
    ]}


@router.post("/announcements", status_code=201)
def create_announcement(data: AnnouncementCreate, db: Database, admin: Administrator):
    title, message = data.title.strip(), data.message.strip()
    if len(title) < 3 or len(message) < 5:
        raise HTTPException(status_code=422, detail="Title and message must not be blank.")
    stmt = select(User.id).where(User.is_active.is_(True))
    if data.audience != "all":
        stmt = stmt.where(User.role == data.audience)
    ids = db.scalars(stmt).all()
    if not ids:
        raise HTTPException(status_code=409, detail="There are no active users in this audience.")
    for user_id in ids:
        db.add(Notification(user_id=user_id, title=title, message=message,
                            notification_type="general", is_read=False, in_app_visible=True))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"recipient_count": len(ids), "audience": data.audience,
            "message": "In-app announcement created. No emails were sent."}
