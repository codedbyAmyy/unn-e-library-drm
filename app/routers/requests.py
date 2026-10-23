from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resource_request import (
    RequestStatus,
    ResourceRequestCreate,
    ResourceRequestListResponse,
    ResourceRequestResponse,
    ResourceRequestReview,
)
from app.services.request_service import (
    RequestError,
    cancel_request,
    create_request,
    get_request,
    list_requests,
    review_request,
)
from app.utils.dependencies import (
    get_current_user,
    require_roles,
)

router = APIRouter(
    prefix="/requests",
    tags=["Resource Requests"],
)

CurrentUser = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]

def handle_error(exc: RequestError):
    raise HTTPException(
        status_code=exc.status_code,
        detail=exc.detail,
    ) from exc

@router.post(
    "",
    response_model=ResourceRequestResponse,
    status_code=201,
)
def submit_resource_request(
    data: ResourceRequestCreate,
    db: Database,
    user: Annotated[
        User,
        Depends(require_roles("student", "lecturer"))
    ],
):
    try:
        return create_request(db, user.id, data)
    except RequestError as exc:
        handle_error(exc)
        
@router.get(
    "",
    response_model=ResourceRequestListResponse,
)
def get_resource_requests(
    db: Database,
    user: CurrentUser,
    status_filter: Annotated[
        RequestStatus | None,
        Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total =list_requests(
        db,
        user_id=user.id,
        is_librarian=user.role in ("librarian, admin"),
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    
    return ResourceRequestListResponse(
        items=items,
        total=total,
    )
    
@router.get(
    "/{request_id}",
    response_model=ResourceRequestResponse,
)
def get_resource_request(
    request_id: int,
    db: Database,
    user: CurrentUser,
):
    try:
        return get_request(
            db,
            request_id,
            user.id,
            user.role in ("librarian", "admin"),
        )
    except RequestError as exc:
        handle_error(exc)

@router.post(
    "/{request_id}/cancel",
    response_model=ResourceRequestResponse,
)   
def cancel_own_request(
    request_id: int,
    db: Database,
    user: Annotated[
        User, Depends(require_roles("student", "lecturer"))
    ],
):
    try:
        return cancel_request(db, request_id, user.id)
    except RequestError as exc:
        handle_error(exc)


@router.patch(
    "/{request_id}/review",
    response_model=ResourceRequestResponse,
)
def librarian_review_request(
    request_id: int,
    data: ResourceRequestReview,
    db: Database,
    user: Annotated[
        User, Depends(require_roles("librarian"))
    ],
):
    try:
        return review_request(
            db, request_id, user.id, data
        )
    except RequestError as exc:
        handle_error(exc)
