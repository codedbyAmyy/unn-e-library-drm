from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from app.schemas.resource_request import (
    ResourceRequestCreate,
    ResourceRequestReview,
)


class RequestError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


TRANSITIONS = {
    "pending": {"under_review", "approved", "rejected"},
    "under_review": {"approved", "rejected"},
    "approved": {"fulfilled", "rejected"},
    "fulfilled": set(),
    "rejected": set(),
    "cancelled": set(),
}


def create_request(
    db: Session,
    user_id: int,
    data: ResourceRequestCreate,
) -> ResourceRequest:
    values = data.model_dump()

    for field in ("title", "resource_type"):
        values[field] = values[field].strip()
        if not values[field]:
            raise RequestError(400, f"{field} cannot be blank.")

    for field in ("author", "description", "reason"):
        if values[field] is not None:
            values[field] = values[field].strip() or None

    request = ResourceRequest(
        **values,
        requested_by=user_id,
        status="pending",
    )

    try:
        db.add(request)
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return request


def list_requests(
    db: Session,
    user_id: int,
    is_librarian: bool,
    status_filter: str | None,
    limit: int,
    offset: int,
):
    filters = []

    if not is_librarian:
        filters.append(ResourceRequest.requested_by == user_id)

    if status_filter:
        filters.append(ResourceRequest.status == status_filter)

    total = db.scalar(
        select(func.count(ResourceRequest.id)).where(*filters)
    ) or 0

    items = db.scalars(
        select(ResourceRequest)
        .where(*filters)
        .order_by(
            ResourceRequest.created_at.desc(),
            ResourceRequest.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return items, total


def get_request(
    db: Session,
    request_id: int,
    user_id: int,
    is_librarian: bool,
) -> ResourceRequest:
    request = db.get(ResourceRequest, request_id)

    if request is None or (
        not is_librarian and request.requested_by != user_id
    ):
        raise RequestError(404, "Resource request not found.")

    return request


def cancel_request(
    db: Session,
    request_id: int,
    user_id: int,
) -> ResourceRequest:
    request = get_request(db, request_id, user_id, False)

    if request.status != "pending":
        raise RequestError(
            409, "Only pending requests can be cancelled."
        )

    try:
        request.status = "cancelled"
        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return request


def review_request(
    db: Session,
    request_id: int,
    reviewer_id: int,
    data: ResourceRequestReview,
) -> ResourceRequest:
    # Lock the row so concurrent reviewers do not overwrite
    # each other's decisions.
    request = db.scalar(
        select(ResourceRequest)
        .where(ResourceRequest.id == request_id)
        .with_for_update()
    )

    if request is None:
        raise RequestError(404, "Resource request not found.")

    if data.status not in TRANSITIONS.get(request.status, set()):
        raise RequestError(
            409,
            f"Cannot change request from {request.status} "
            f"to {data.status}.",
        )

    notes = (
        data.review_notes.strip()
        if data.review_notes is not None else None
    )

    if data.status == "rejected" and not notes:
        raise RequestError(
            400, "Rejection requires review notes."
        )

    if data.status == "fulfilled":
        if data.fulfilled_resource_id is None:
            raise RequestError(
                400, "Fulfilment requires a resource ID."
            )

        resource = db.get(
            Resource, data.fulfilled_resource_id
        )

        if (
            resource is None
            or not resource.is_published
            or resource.is_archived
        ):
            raise RequestError(
                400,
                "The fulfilment resource must be published "
                "and available.",
            )
    elif data.fulfilled_resource_id is not None:
        raise RequestError(
            400,
            "A fulfilment resource ID is only valid "
            "when fulfilling a request.",
        )

    try:
        request.status = data.status
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.now(timezone.utc)
        request.review_notes = notes

        if data.status == "fulfilled":
            request.fulfilled_resource_id = (
                data.fulfilled_resource_id
            )

        db.commit()
        db.refresh(request)
    except Exception:
        db.rollback()
        raise

    return request
