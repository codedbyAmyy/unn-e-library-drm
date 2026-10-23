from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class ReadingListCreate(BaseModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    academic_session: str | None = Field(
        default=None, max_length=30
    )
    
class ReadingListUpdate(BaseModel):
    title: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    description: str | None = None
    academic_session: str | None = Field(
        default=None, max_length=30
    )
    
class ReadingListItemCreate(BaseModel):
    resource_id: int = Field(gt=0)
    notes: str | None = None
    is_required: bool = False
    
class ReadingListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    resource_id: int
    position: int
    notes: str | None
    is_required: bool
    created_at: datetime
    
class ReadingListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    course_id: int
    title: str
    description: str | None
    academic_session: str | None
    created_by: int
    is_published: bool
    created_at: datetime
    updated_at: datetime
    items: list[ReadingListItemResponse]
    
class ReadingListCollection(BaseModel):
    total: int
    items: list[ReadingListResponse]