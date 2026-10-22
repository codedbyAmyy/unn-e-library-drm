
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    UnreadCountResponse,
)
from app.utils.dependencies import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

CurrentUser = Annotated[User, Depends(get_current_user)]
DatabaseSession = Annotated[Session, Depends(get_db)]


def visible_to_user(user_id: int):
    return (
        Notification.user_id == user_id,
        Notification.in_app_visible.is_(True),
    )


def get_preference(db: Session, user_id: int):
    return db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )


def preference_response(preference):
    if preference is None:
        return NotificationPreferenceResponse(
            new_resource_in_app=True,
            new_resource_email=True,
        )

    return NotificationPreferenceResponse(
        new_resource_in_app=preference.new_resource_in_app,
        new_resource_email=preference.new_resource_email,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user: CurrentUser,
    db: DatabaseSession,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    filters = list(visible_to_user(current_user.id))

    if unread_only:
        filters.append(Notification.is_read.is_(False))

    total = db.scalar(
        select(func.count(Notification.id)).where(*filters)
    ) or 0

    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            *visible_to_user(current_user.id),
            Notification.is_read.is_(False),
        )
    ) or 0

    items = db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return NotificationListResponse(
        items=[
            NotificationResponse.model_validate(item)
            for item in items
        ],
        total=total,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
def get_unread_count(
    current_user: CurrentUser,
    db: DatabaseSession,
):
    count = db.scalar(
        select(func.count(Notification.id)).where(
            *visible_to_user(current_user.id),
            Notification.is_read.is_(False),
        )
    ) or 0

    return UnreadCountResponse(unread_count=count)


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def read_preferences(
    current_user: CurrentUser,
    db: DatabaseSession,
):
    return preference_response(
        get_preference(db, current_user.id)
    )


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def update_preferences(
    changes: NotificationPreferenceUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
):
    updates = changes.model_dump(exclude_unset=True)

    if not updates or any(
        value is None for value in updates.values()
    ):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one valid preference.",
        )

    preference = get_preference(db, current_user.id)

    if preference is None:
        preference = NotificationPreference(
            user_id=current_user.id,
        )
        db.add(preference)

    for field, value in updates.items():
        setattr(preference, field, value)

    try:
        db.commit()
        db.refresh(preference)
    except Exception:
        db.rollback()
        raise

    return preference_response(preference)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            *visible_to_user(current_user.id),
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)

        try:
            db.commit()
            db.refresh(notification)
        except Exception:
            db.rollback()
            raise

    return notification
