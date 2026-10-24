from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.reading import Bookmark, ReadingHistory
from app.models.resource import Resource
from app.models.user import User
from app.schemas.resource import ResourceResponse

def visible_resource(
    db: Session,
    resource_id: int
) -> Resource:
    resource = db.get(Resource, resource_id)
    
    if (
        resource is None
        or not resource.is_published
        or resource.is_archived
    ):
        raise HTTPException(
            status_code=404,
            detail="Resource not found."
        )
    return resource

def create_bookmark(
    db: Session,
    user_id: int,
    resource_id: int,
) -> Bookmark:
    visible_resource(db, resource_id)
    
    existing = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.resource_id == resource_id,
        )
    )
    
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Resource is already bookmarked."
        )
    bookmark = Bookmark(
        user_id=user_id,
        resource_id=resource_id
    )
    
    try:
        db.add(bookmark)
        db.commit()
        db.refresh(bookmark)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Resource is already bookmarked."
        ) from exc
    except Exception:
        db.rollback()
        raise
    return bookmark

def remove_bookmark(
    db: Session,
    user_id: int,
    resource_id: int,
) -> None:
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user_id,
            Bookmark.resource_id == resource_id,
        )
    )
    if bookmark is None:
        raise HTTPException(
            status_code=404, detail="Bookmark not found."
        )
    try:
        db.delete(bookmark)
        db.commit()
    except Exception:
        db.rollback()
        raise
    
def list_bookmarks(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
):
    filters = (
        Bookmark.user_id == user_id,
        Resource.is_published.is_(True),
        Resource.is_archived.is_(False),
    )
    
    total = db.scalar(
        select(func.count(Bookmark.id))
        .join(
            Resource, 
            Bookmark.resource_id == Resource.id
        )
        .where(*filters)
    ) or 0
    
    items = db.scalars(
        select(Bookmark)
        .join(
            Resource, 
            Bookmark.resource_id == Resource.id
        )
        .where(*filters)
        .order_by(
            Bookmark.created_at.desc(), 
            Bookmark.id.desc()
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return list(items), total

def record_successful_read(
    db: Session,
    user_id: int,
    resource_id: int,
) -> ReadingHistory:
    """Record one successful protected-PDF opening."""
    # The DRM layer must have granted access before this runs
    entry = ReadingHistory(
        user_id=user_id,
        resource_id=resource_id,
        duration_seconds=0
    )
    
    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        raise
    return entry

def list_reading_history(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
):
    total = db.scalar(
        select(func.count(ReadingHistory.id))
        .where(ReadingHistory.user_id == user_id)
    ) or 0

    items = db.scalars(
        select(ReadingHistory)
        .where(ReadingHistory.user_id == user_id)
        .order_by(
            ReadingHistory.last_read_at.desc(),
            ReadingHistory.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return list(items), total


def recommend_resources(
    db: Session,
    user: User,
    limit: int = 10,
):
    """
    Explainable hybrid content-based scoring.

    Academic relevance: department/course.
    Behavioral relevance: bookmarked/read categories,
    courses, departments and resource types.
    Cold start: academic relevance + featured/new items.

    Excludes already-read resources where possible.
    """

    bookmarked_ids = set(
        db.scalars(
            select(Bookmark.resource_id)
            .where(Bookmark.user_id == user.id)
        ).all()
    )

    history_ids = db.scalars(
        select(ReadingHistory.resource_id)
        .where(ReadingHistory.user_id == user.id)
        .order_by(ReadingHistory.last_read_at.desc())
        .limit(100)
    ).all()

    read_ids = set(history_ids)
    interest_ids = bookmarked_ids | read_ids

    interests = []

    if interest_ids:
        interests = db.scalars(
            select(Resource)
            .where(Resource.id.in_(interest_ids))
        ).all()

    category_counts = Counter(
        item.category_id
        for item in interests
        if item.category_id is not None
    )
    course_counts = Counter(
        item.course_id
        for item in interests
        if item.course_id is not None
    )
    department_counts = Counter(
        item.department_id
        for item in interests
        if item.department_id is not None
    )
    type_counts = Counter(
        item.resource_type
        for item in interests
    )

    candidates = db.scalars(
        select(Resource)
        .where(
            Resource.is_published.is_(True),
            Resource.is_archived.is_(False),
        )
        .order_by(
            Resource.is_featured.desc(),
            Resource.created_at.desc(),
            Resource.id.desc(),
        )
        .limit(500)
    ).all()

    scored = []

    for resource in candidates:
        if resource.id in read_ids:
            continue

        score = 0
        reasons = []

        # Academic matching
        if (
            user.department_id is not None
            and resource.department_id == user.department_id
        ):
            score += 50
            reasons.append("Relevant to your department")

        if (
            resource.course_id is not None
            and course_counts[resource.course_id] > 0
        ):
            score += 35
            reasons.append("Related to your course materials")

        if (
            resource.category_id is not None
            and category_counts[resource.category_id] > 0
        ):
            score += 25
            reasons.append("Similar to your saved or read subjects")

        if (
            resource.department_id is not None
            and department_counts[resource.department_id] > 0
        ):
            score += 15
            reasons.append("Matches your reading interests")

        if type_counts[resource.resource_type] > 0:
            score += 5
            reasons.append("Similar resource type")

        if resource.is_featured:
            score += 10
            reasons.append("Featured library resource")

        if resource.id in bookmarked_ids:
            score += 5
            reasons.append("In your bookmarks")

        reason = (
            reasons[0]
            if reasons
            else "Available in your university library"
        )

        scored.append((score, resource, reason))

    scored.sort(
        key=lambda entry: (
            -entry[0],
            -(entry[1].id),
        )
    )

    return [
        {
            "resource": ResourceResponse.model_validate(resource),
            "score": score,
            "reason": reason,
        }
        for score, resource, reason in scored[:limit]
    ]