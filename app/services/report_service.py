from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.report import BrokenResourceReport
from app.models.resource import Resource
from app.models.user import User
from app.schemas.report import (
    BrokenReportCreate,
    BrokenReportReview,
)

def report_error(code: int, message: str):
    raise HTTPException(
        status_code=code,
        detail=message,
    )

def create_report(
    db: Session,
    user: User,
    data: BrokenReportCreate,
) -> BrokenResourceReport:
    resource = db.get(Resource, data.resource_id)
    if (
        resource is None
        or not resource.is_published
        or resource.is_archived
    ):
        report_error(404, "Resource not found or unavailable.")
        
    description = (
        data.description.strip()
        if data.description is not None
        else None
    )
    
    if data.issue_type == "other" and not description:
        report_error(422, "Please describe the issue when selecting 'other'.")
        
    report = BrokenResourceReport(
        reported_by=user.id,
        resource_id=data.resource_id,
        issue_type=data.issue_type,
        description=description or None,
        status="open",
    )
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        raise
    return report

def list_reports(
    db: Session,
    user: User,
    status_filter: str | None,
    limit: int,
    offset: int,
):
    filters = []
    
    # Students and lecturers only see their own reports.
    if user.role not in ("librarian", "admin"):
        filters.append(
            BrokenResourceReport.reported_by == user.id
        )
    if status_filter is not None:
        filters.append(
            BrokenResourceReport.status == status_filter
        )
    total = db.scalar(
        select(func.count(BrokenResourceReport.id)).where(*filters)
    ) or 0
    
    items = db.scalars(
        select(BrokenResourceReport)
        .where(*filters)
        .order_by(
            BrokenResourceReport.created_at.desc(),
            BrokenResourceReport.id.desc()
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return items, total

def get_report(
    db: Session,
    report_id: int,
    user: User,
) -> BrokenResourceReport:
    report = db.get(
        BrokenResourceReport, report_id
    )
    
    if report is None:
        report_error(404, "Report not found.")
        
    if (
        user.role not in ("librarian", "admin")
        and report.reported_by != user.id
    ):
        report_error(404, "Report not found.")
    return report

ALLOWED_TRANSITIONS = {
    "open": {
        "under_review",
        "resolved",
        "dismissed",
    },
    "under_review": {
        "resolved",
        "dismissed",
    },
    "resolved": set(),
    "dismissed": set(),
}

def review_report(
    db: Session,
    report_id: int,
    librarian_id: int,
    data: BrokenReportReview,
) -> BrokenResourceReport:
    report = db.scalar(
        select(BrokenResourceReport)
        .where(BrokenResourceReport.id == report_id)
        .with_for_update()
    )
    
    if report is None:
        report_error(404, "Report not found.")
    
    allowed = ALLOWED_TRANSITIONS.get(
        report.status, set()
    )
    
    if data.status not in allowed:
        report_error(409, f"Cannot change report from {report.status} to {data.status}.")
        
    notes = (
        data.resolution_notes.strip()
        if data.resolution_notes is not None
        else None
    )
    
    if data.status in ("resolved", "dismissed"):
        if not notes:
            report_error(400, "Resolution notes are required when closing a report.")
    try:
        report.status = data.status
        report.reviewed_by = librarian_id
        report.resolution_notes = notes or None
        
        if data.status in ("resolved", "dismissed"):
            report.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        raise
    return report