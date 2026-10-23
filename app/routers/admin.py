from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUserListResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.auth import UserResponse
from app.services.admin_service import (
    get_user,
    list_users,
    update_user_role,
    update_user_status,
)
from app.utils.dependencies import require_roles


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
)

Database = Annotated[Session, Depends(get_db)]
Administrator = Annotated[User, Depends(require_roles("admin"))]

@router.get(
    "/users",
    response_model=AdminUserListResponse,
)
def browse_users(
    db: Database,
    admin: Administrator,
    role: Literal[
        "student", "lecturer", "librarian", "admin"
    ] | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0
):
    users, total = list_users(
        db,
        role=role,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )
    return AdminUserListResponse(
        total=total,
        items=users,
    )

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
)
def read_user(
    user_id: int,
    db: Database,
    admin: Administrator,
):
    return get_user(db, user_id)

@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
)
def change_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Database,
    admin: Administrator,
):
    return update_user_status(
        db,
        user_id=user_id,
        admin_id=admin.id,
        is_active=data.is_active,
    )

@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
)
def change_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: Database,
    admin: Administrator,
):
    return update_user_role(
        db,
        user_id=user_id,
        admin_id=admin.id,
        new_role=data.role,
    )