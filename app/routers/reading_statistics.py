"""Exact current-user reading summaries; no record-limit undercounts."""
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.reading import ReadingHistory
from app.models.reading_progress import ReadingProgress
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/reading-statistics", tags=["Reading Statistics"])

class ReadingSummary(BaseModel):
    reading_records: int
    unique_resources: int
    recorded_duration_seconds: int
    completed_pdfs: int
    tracked_pdfs: int

@router.get("/me", response_model=ReadingSummary)
def my_reading_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    records, unique, duration = db.execute(
        select(
            func.count(ReadingHistory.id),
            func.count(func.distinct(ReadingHistory.resource_id)),
            func.coalesce(func.sum(ReadingHistory.duration_seconds), 0),
        ).where(ReadingHistory.user_id == user.id)
    ).one()
    tracked, completed = db.execute(
        select(
            func.count(ReadingProgress.id),
            func.count(ReadingProgress.id).filter(
                ReadingProgress.total_pages > 0,
                ReadingProgress.current_page >= ReadingProgress.total_pages,
            ),
        ).where(ReadingProgress.user_id == user.id)
    ).one()
    return ReadingSummary(
        reading_records=int(records),
        unique_resources=int(unique),
        recorded_duration_seconds=int(duration),
        tracked_pdfs=int(tracked),
        completed_pdfs=int(completed),
    )
