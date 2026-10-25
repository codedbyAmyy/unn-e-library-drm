"""Per-user, per-resource verified reader position. PDF remains on existing protected endpoint."""
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.resource import Resource, ResourceFile
from app.models.reading_progress import ReadingProgress
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/reading-progress", tags=["Reading Progress"])

class Position(BaseModel):
    current_page: int = Field(ge=1)
    total_pages: int = Field(ge=1, le=100000)

class ProgressResponse(BaseModel):
    resource_id: int
    current_page: int | None
    total_pages: int | None
    updated_at: datetime | None

def _resource(db: Session, resource_id: int, user: User):
    resource = db.get(Resource, resource_id)
    if resource is None or resource.is_archived:
        raise HTTPException(404, "Resource not found.")
    if not resource.is_published and user.role not in ("librarian", "admin"):
        raise HTTPException(404, "Resource not found.")
    return resource

def _response(resource_id, row):
    return ProgressResponse(resource_id=resource_id,
        current_page=row.current_page if row else None,
        total_pages=row.total_pages if row else None,
        updated_at=row.updated_at if row else None)

@router.get("/{resource_id}", response_model=ProgressResponse)
def get_progress(resource_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]):
    _resource(db, resource_id, user)
    row = db.scalar(select(ReadingProgress).where(
        ReadingProgress.user_id == user.id, ReadingProgress.resource_id == resource_id))
    return _response(resource_id, row)

@router.put("/{resource_id}", response_model=ProgressResponse)
def save_progress(resource_id: int, position: Position,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]):
    _resource(db, resource_id, user)
    if position.current_page > position.total_pages:
        raise HTTPException(422, "Current page cannot exceed the PDF page count.")
    registered_count = db.scalar(select(ResourceFile.page_count).where(
        ResourceFile.resource_id == resource_id,
        ResourceFile.is_primary.is_(True)).order_by(ResourceFile.id.desc()).limit(1))
    if registered_count is not None and registered_count > 0 and position.total_pages != registered_count:
        raise HTTPException(409, "Page count differs from the currently registered PDF.")
    row = db.scalar(select(ReadingProgress).where(
        ReadingProgress.user_id == user.id, ReadingProgress.resource_id == resource_id))
    if row is None:
        row = ReadingProgress(user_id=user.id, resource_id=resource_id,
            current_page=position.current_page, total_pages=position.total_pages)
        db.add(row)
    else:
        row.current_page = position.current_page
        row.total_pages = position.total_pages
        row.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return _response(resource_id, row)
