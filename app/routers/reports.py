from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.report import (
    BrokenReportCollection,
    BrokenReportCreate,
    BrokenReportResponse,
    BrokenReportReview,
    ReportStatus,
)
from app.services.report_service import (
    create_report,
    get_report,
    list_reports,
    review_report,
)
from app.utils.dependencies import (
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/reports", tags=["Broken Resource Reports"])

Database = Annotated[
    Session,
    Depends(get_db)
]

CurrentUser = Annotated[
    User,
    Depends(get_current_user)
]

Reporter = Annotated[
    User,
    Depends(require_roles("student", "lecturer")),
]

Librarian = Annotated[
    User,
    Depends(require_roles("librarian"))
]

@router.post(
    "",
    response_model=BrokenReportResponse,
    status_code=201,
)
def submit_report(
    data: BrokenReportCreate,
    db: Database,
    user: Reporter,
):
    return create_report(db, user, data)

@router.get(
    "",
    response_model=BrokenReportCollection,
)
def browse_reports(
    db: Database,
    user: CurrentUser,
    status_filter: Annotated[
        ReportStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0
):
    items, total = list_reports(
        db,
        user,
        status_filter,
        limit,
        offset,
    )
    
    return BrokenReportCollection(
        total=total,
        items=items
    )
    
@router.get(
    "/{report_id}",
    response_model=BrokenReportResponse,
)
def get_report_detail(
    report_id: int,
    db: Database,
    user: CurrentUser,
):
    return get_report(db, report_id, user)

@router.patch(
    "/{report_id}/review",
    response_model=BrokenReportResponse
)
def librarian_review_report(
    report_id: int,
    data: BrokenReportReview,
    db: Database,
    user: Librarian
):
    return review_report(
        db,
        report_id,
        user.id,
        data
    )