
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str | None
    notification_type: str
    resource_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    new_resource_in_app: bool
    new_resource_email: bool


class NotificationPreferenceUpdate(BaseModel):
    new_resource_in_app: bool | None = None
    new_resource_email: bool | None = None
