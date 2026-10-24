from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.personalization import (
    BookmarkListResponse,
    BookmarkResponse,
    ReadingHistoryListResponse,
    RecommendationListResponse,
)
from app.services.personalization_service import (
    create_bookmark,
    remove_bookmark,
    list_bookmarks,
    list_reading_history,
    recommend_resources,
)
from app.utils.dependencies import get_current_user


router = APIRouter(
    tags=["Personalization"],
)

Database = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/bookmarks/{resource_id}",
    response_model=BookmarkResponse,
    status_code=201,
)
def save_bookmark(
    resource_id: int,
    db: Database,
    user: CurrentUser,
):
    return create_bookmark(db, user.id, resource_id)


@router.get(
    "/bookmarks",
    response_model=BookmarkListResponse,
)
def my_bookmarks(
    db: Database,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = list_bookmarks(
        db, user.id, limit, offset
    )
    return BookmarkListResponse(
        total=total,
        items=items,
    )


@router.delete(
    "/bookmarks/{resource_id}",
    status_code=204,
)
def delete_bookmark(
    resource_id: int,
    db: Database,
    user: CurrentUser,
):
    remove_bookmark(db, user.id, resource_id)
    return Response(status_code=204)


@router.get(
    "/reading-history",
    response_model=ReadingHistoryListResponse,
)
def my_reading_history(
    db: Database,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = list_reading_history(
        db, user.id, limit, offset
    )
    return ReadingHistoryListResponse(
        total=total,
        items=items,
    )


@router.get(
    "/recommendations/me",
    response_model=RecommendationListResponse,
)
def my_recommendations(
    db: Database,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
):
    return RecommendationListResponse(
        items=recommend_resources(db, user, limit)
    )