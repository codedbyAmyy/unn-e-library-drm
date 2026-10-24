from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.resource import ResourceResponse

from app.schemas.resource import ResourceResponse

class BookmarkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    resource_id: int
    created_at: datetime
    
class BookmarkListResponse(BaseModel):
    total: int
    items: list[BookmarkResponse]
    
class ReadingHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    resource_id: int
    started_at: datetime
    last_read_at: datetime
    duration_seconds: int
    
class ReadingHistoryListResponse(BaseModel):
    total: int
    items: list[ReadingHistoryResponse]
    
class RecommendedResource(BaseModel):
    resource: ResourceResponse
    score: int
    reason: str
    
class RecommendationListResponse(BaseModel):
    items: list[RecommendedResource]