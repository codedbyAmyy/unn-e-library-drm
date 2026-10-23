from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.reading_list import (
    ReadingListCollection,
    ReadingListCreate,
    ReadingListItemCreate,
    ReadingListResponse,
    ReadingListUpdate,
)
from app.services.reading_list_service import (
    add_reading_item,
    create_reading_list,
    get_visible_list,
    list_reading_lists,
    remove_reading_item,
    set_publication,
    update_reading_list,
)
from app.utils.dependencies import (
    get_current_user,
    require_roles,
)

router = APIRouter(
    prefix="/reading-lists",
    tags=["Course Reading Lists"],
)

Database = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Editor = Annotated[
    User, Depends(require_roles("lecturer", "librarian"))
]

@router.post(
    "",
    response_model=ReadingListResponse,
    status_code=201,
)
def create_list(
    data: ReadingListCreate,
    db: Database,
    user: Editor,
):
    return create_reading_list(db, user, data)

@router.get(
    "",
    response_model=ReadingListCollection
)
def browse_lists(
    db: Database,
    user: CurrentUser,
    course_id: Annotated[
        int | None, Query(gt=0)
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0
):
    items, total = list_reading_lists(
        db, user, limit, offset, course_id
    )
    return ReadingListCollection(
        total=total,
        items=items
    )

@router.get(
    "/{reading_list_id}",
    response_model=ReadingListResponse,
)
def read_list(
    reading_list_id: int,
    db: Database,
    user: CurrentUser,
):
    return get_visible_list(db, reading_list_id, user)

@router.patch(
    "/{reading_list_id}",
    response_model=ReadingListResponse,
)
def edit_list(
    reading_list_id: int,
    data: ReadingListUpdate,
    db: Database,
    user: Editor,
):
    return update_reading_list(
        db, reading_list_id, user, data
    )
    
@router.post(
    "/{reading_list_id}/items",
    response_model=ReadingListResponse,
    status_code=201,
)
def add_item(
    reading_list_id: int,
    data: ReadingListItemCreate,
    db: Database,
    user: Editor,
):
    return add_reading_item(
        db, reading_list_id, user, data
    )
    
@router.delete(
    "/{reading_list_id}/items/{item_id}",
    status_code=204
)
def remove_item(
    reading_list_id: int,
    item_id: int,
    db: Database,
    user: Editor,
):
    remove_reading_item(
        db, reading_list_id, item_id, user
    )

@router.post(
    "/{reading_list_id}/publish",
    response_model=ReadingListResponse,
)
def publish_list(
    reading_list_id: int,
    db: Database,
    user: Editor,
):
    return set_publication(
        db, reading_list_id, user, True
    )

@router.post(
    "/{reading_list_id}/unpublish",
    response_model=ReadingListResponse,
)
def unpublish_list(
    reading_list_id: int,
    db: Database,
    user: Editor,
):
    return set_publication(
        db, reading_list_id, user, False
    )