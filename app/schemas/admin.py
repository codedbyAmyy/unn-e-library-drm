from typing import Literal

from pydantic import BaseModel
from app.schemas.auth import UserResponse as AdminUserResponse

class UserStatusUpdate(BaseModel):
    is_active: bool
    
class UserRoleUpdate(BaseModel):
    role: Literal["student", "lecturer", "librarian"]
    
class AdminUserListResponse(BaseModel):
    total: int
    items: list["AdminUserResponse"]
    
AdminUserListResponse.model_rebuild()
    