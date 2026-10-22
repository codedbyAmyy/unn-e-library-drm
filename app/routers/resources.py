from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resource import(
    ResourceCreateRequest,
    ResourceResponse,
    ResourceUpdateRequest,
)

from app.services.resource_service import (
    create_resource,
    update_resource,
    publish_resource,
    unpublish_resource,
)

from app.services.storage_service import (
    upload_and_register_resource_file,
    MAX_FILE_SIZE_BYTES,
)
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

@router.post(
    "/{resource_id}/files",
    status_code=status.HTTP_201_CREATED,
)
def upload_resource_file_endpoint(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_roles("librarian"))
    ],
    file: Annotated[UploadFile, File(...)],
):
    """Upload a PDF file for a resource. Librarians only."""
    try:
        file_content = file.file.read(MAX_FILE_SIZE_BYTES + 1)

        if len(file_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The file must not exceed 50 MB.",
            )

        file_record = upload_and_register_resource_file(
            db=db,
            resource_id=resource_id,
            filename=file.filename or "",
            file_content=file_content,
            content_type=file.content_type or "",
            is_primary=True,
        )

        return {
            "message": "Resource file uploaded successfully.",
            "file": {
                "id": file_record.id,
                "resource_id": file_record.resource_id,
                "original_filename": file_record.original_filename,
                "mime_type": file_record.mime_type,
                "file_size_bytes": file_record.file_size_bytes,
                "checksum_sha256": file_record.checksum_sha256,
                "is_primary": file_record.is_primary,
            },
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to upload the resource file.",
        ) from exc

    finally:
        file.file.close()

@router.patch("/{resource_id}", response_model=ResourceResponse)
def update_library_resource(
    resource_id: int,
    resource_data: ResourceUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles("librarian")),
    ],
):
    """Update library resource metadata. Restricted to librarians."""

    try:
        return update_resource(
            db=db,
            resource_id=resource_id,
            resource_data=resource_data,
        )
    except ValueError as exc:
        if str(exc) == "Resource not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with the supplied ISBN or DOI already exists.",
        ) from exc

@router.post(
    "/{resource_id}/publish",
    response_model=ResourceResponse,
)
def publish_library_resources(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles("librarian"))
    ],
):
    """Publish a resource with an uploaded PDF. Librarians only."""
    try:
        return publish_resource(
            db=db,
            resource_id=resource_id,
        )
    except ValueError as exc:
        if str(exc) == "Resource not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

@router.post(
    "/{resource_id}/unpublish",
    response_model=ResourceResponse,
)
def unpublish_library_resource(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles("librarian")),
    ]
):
    """Unpublish a resource. Restricted to librarians."""
    try:
        return unpublish_resource(
            db=db,
            resource_id=resource_id,
        )
    except ValueError as exc:
        if str(exc) == "Resource not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc