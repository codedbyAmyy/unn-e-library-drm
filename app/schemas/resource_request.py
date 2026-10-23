from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequestStatus = Literal[
    "pending", "under_review", "approved",
    "fulfilled", "rejected", "cancelled",
]


class ResourceRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, max_length=200)
    resource_type: str = Field(min_length=1, max_length=50)
    description: str | None = None
    reason: str | None = None


class ResourceRequestReview(BaseModel):
    status: Literal[
        "under_review", "approved", "rejected", "fulfilled"
    ]
    review_notes: str | None = None
    fulfilled_resource_id: int | None = Field(default=None, gt=0)


class ResourceRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by: int
    title: str
    author: str | None
    resource_type: str
    description: str | None
    reason: str | None
    status: str
    reviewed_by: int | None
    review_notes: str | None
    fulfilled_resource_id: int | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None


class ResourceRequestListResponse(BaseModel):
    total: int
    items: list[ResourceRequestResponse]
