
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drm import DownloadRecord
from app.models.resource import Resource, ResourceFile
from app.services.storage_service import download_private_pdf
from app.services.watermark_service import watermark_pdf


class DRMAccessError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def record_access(
    db: Session,
    *,
    user_id: int,
    resource_id: int,
    access_type: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a DRM access event."""

    record = DownloadRecord(
        user_id=user_id,
        resource_id=resource_id,
        access_type=access_type,
        ip_address=ip_address,
        user_agent=(
            user_agent[:500] if user_agent else None
        ),
    )

    try:
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_protected_pdf(
    db: Session,
    *,
    resource_id: int,
    user_id: int,
    access_type: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> bytes:
    """Authorize access and return an identifiable PDF."""

    if access_type not in ("view", "download"):
        raise ValueError("Invalid access type.")

    resource = db.get(Resource, resource_id)

    if resource is None:
        raise DRMAccessError(404, "Resource not found.")

    event_data = {
        "user_id": user_id,
        "resource_id": resource_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }

    if not resource.is_published or resource.is_archived:
        record_access(
            db,
            access_type="blocked",
            **event_data,
        )
        raise DRMAccessError(
            403,
            "This resource is not available for access.",
        )

    file_record = db.scalar(
        select(ResourceFile)
        .where(
            ResourceFile.resource_id == resource_id,
            ResourceFile.mime_type == "application/pdf",
        )
        .order_by(
            ResourceFile.is_primary.desc(),
            ResourceFile.id.asc(),
        )
    )

    if file_record is None:
        record_access(
            db,
            access_type="blocked",
            **event_data,
        )
        raise DRMAccessError(
            404,
            "No PDF file is available for this resource.",
        )

    try:
        original_pdf = download_private_pdf(
            file_record.storage_path
        )
        protected_pdf = watermark_pdf(
            original_pdf,
            user_id,
        )
    except Exception as exc:
        raise DRMAccessError(
            502,
            "Unable to prepare the protected PDF.",
        ) from exc

    record_access(
        db,
        access_type=access_type,
        **event_data,
    )

    return protected_pdf
