from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

IssueType = Literal[
    "file_unavailable",
    "file_corrupted",
    "incorrect_metadata",
    "access_problem",
    "other"
]

ReportStatus = Literal[
    "open",
    "under_review",
    "resolved",
    "dismissed",
]

class BrokenReportCreate(BaseModel):
    resource_id: int = Field(gt=0)
    issue_type: IssueType
    description: str | None = Field(
        default=None, max_length=2000
    )
    
class BrokenReportReview(BaseModel):
    status: Literal[
        "under_review", "resolved", "dismissed"
    ]
    resolution_notes: str | None = Field(
        default=None, max_length=2000
    )
    
class BrokenReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    reported_by: int
    resource_id: int
    issue_type: IssueType
    description: str | None
    status: ReportStatus
    reviewed_by: int | None
    resolution_notes: str | None
    created_at: datetime
    resolved_at: datetime | None
    
class BrokenReportCollection(BaseModel):
    total: int
    items: list[BrokenReportResponse]