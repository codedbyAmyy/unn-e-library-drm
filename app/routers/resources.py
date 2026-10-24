import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.resource import(
    ResourceCreateRequest,
    ResourceResponse,
    ResourceUpdateRequest,
    ResourceListResponse,
)

from app.services.resource_service import (
    create_resource,
    update_resource,
    publish_resource,
    unpublish_resource,
    archive_resource,
    unarchive_resource,
)

from app.services.storage_service import (
    upload_and_register_resource_file,
    MAX_FILE_SIZE_BYTES,
)
from app.services.catalogue_service import (
    list_catalogue_resources,
    get_catalogue_resource,
)
from app.services.drm_service import (
    DRMAccessError,
    get_protected_pdf,
)
from app.services.personalization_service import record_successful_read
from app.utils.dependencies import require_roles, get_current_user

router = APIRouter(prefix="/resources", tags=["Resources"])

logger = logging.getLogger(__name__)

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
        
@router.post(
    "/{resource_id}/archive",
    response_model=ResourceResponse,
)
def archive_library_resource(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles("librarian")),
    ]
):
    """Archive a resource. Librarians only."""
    try:
        return archive_resource(db, resource_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if str(exc) == "Resource not found."
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc)
        ) from exc
        
@router.post(
    "/{resource_id}/unarchive",
    response_model=ResourceResponse,
)
def unarchive_library_resource(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles("librarian")),
    ],
):
    """Restore an archived resource to draft status."""
    try:
        return unarchive_resource(db, resource_id)
    
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if str(exc) == "Resource not found."
                else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc
        

@router.get(
    "",
    response_model=ResourceListResponse,
)
def list_library_resources(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
    search: Annotated[str | None, Query(max_length=200)] = None,
    resource_type: Annotated[str | None, Query()] = None,
    category_id: Annotated[int | None, Query(gt=0)] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    faculty_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Search and list resources according to the user's role."""

    can_manage = current_user.role in (
        "librarian", "admin"
    )

    resources, total = list_catalogue_resources(
        db,
        can_manage=can_manage,
        search=search,
        resource_type=resource_type,
        category_id=category_id,
        department_id=department_id,
        faculty_id=faculty_id,
        limit=limit,
        offset=offset,
    )

    return ResourceListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            ResourceResponse.model_validate(resource)
            for resource in resources
        ],
    )


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
)
def get_library_resource(
    resource_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
):
    """Retrieve a resource while enforcing catalogue visibility."""

    can_manage = current_user.role in (
        "librarian", "admin"
    )

    resource = get_catalogue_resource(
        db,
        resource_id,
        can_manage=can_manage,
    )

    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )

    return resource

def serve_protected_resource(
    resource_id: int,
    db: Session,
    current_user: User,
    request: Request,
    access_type: str,
):
    """Return a protected PDF after authorization."""
    try:
        pdf_bytes = get_protected_pdf(
            db,
            resource_id=resource_id,
            user_id=current_user.id,
            access_type=access_type,
            ip_address=(
                request.client.host
                if request.client else None
            ),
            user_agent=request.headers.get("user-agent"),
        )
    except DRMAccessError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc
    
    # The protected PDF has already been generated successfully.
    # Track successful reads, but never block legitimate DRM
    # access because activity logging encountered a DB error.
    if access_type == "view":
        try:
            record_successful_read(
                db,
                user_id=current_user.id,
                resource_id=resource_id,
            )
        except Exception:
            logger.exception(
                "Reading history recording failed for resource %s",
                resource_id,
            )

    disposition = (
        "inline" if access_type == "view"
        else "attachment"
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'{disposition}; filename="resource-{resource_id}.pdf"'
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.get("/{resource_id}/read")
def read_library_resource(
    resource_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
):
    """Read a protected and watermarked PDF."""

    return serve_protected_resource(
        resource_id,
        db,
        current_user,
        request,
        "view",
    )


@router.get("/{resource_id}/download")
def download_library_resource(
    resource_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(get_current_user)
    ],
):
    """Download an authorized, watermarked PDF."""

    return serve_protected_resource(
        resource_id,
        db,
        current_user,
        request,
        "download",
    )
