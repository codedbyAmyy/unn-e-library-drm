from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resource import ResourceCreateRequest, ResourceResponse
from app.services.resource_service import create_resource
from app.utils.dependencies import require_roles

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.post(
    "",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_library_resources(
    resource_data: ResourceCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles("librarian"))]
):
    """Create a library resource. Restricted to librarians."""
    try:
        return create_resource(
            db=db,
            resource_data=resource_data,
            uploader_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with the supplied ISBN or DOI already exists."
        ) from exc