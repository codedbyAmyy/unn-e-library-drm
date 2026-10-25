from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.academic import Department
from app.models.resource import Resource, ResourceAuthor

SearchField = Literal["all", "title", "author", "isbn", "doi", "abstract"]


def list_catalogue_resources(
    db: Session,
    *,
    can_manage: bool,
    search: str | None = None,
    search_field: SearchField = "all",
    resource_type: str | None = None,
    category_id: int | None = None,
    department_id: int | None = None,
    faculty_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Resource], int]:
    """Return role-visible catalogue matches with field-specific searching."""
    query = select(Resource)
    if not can_manage:
        query = query.where(
            Resource.is_published.is_(True), Resource.is_archived.is_(False)
        )

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        fields = {
            "title": Resource.title.ilike(pattern),
            "author": Resource.authors.any(
                ResourceAuthor.author_name.ilike(pattern)
            ),
            "isbn": Resource.isbn.ilike(pattern),
            "doi": Resource.doi.ilike(pattern),
            "abstract": Resource.abstract.ilike(pattern),
        }
        if search_field == "all":
            query = query.where(or_(*fields.values()))
        else:
            query = query.where(fields[search_field])

    if resource_type is not None:
        query = query.where(Resource.resource_type == resource_type)
    if category_id is not None:
        query = query.where(Resource.category_id == category_id)
    if department_id is not None:
        query = query.where(Resource.department_id == department_id)
    if faculty_id is not None:
        department_ids = select(Department.id).where(
            Department.faculty_id == faculty_id
        )
        query = query.where(Resource.department_id.in_(department_ids))

    total = db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    resources = db.scalars(
        query.order_by(Resource.created_at.desc(), Resource.id.desc())
        .offset(offset).limit(limit)
    ).all()
    return list(resources), total


def get_catalogue_resource(
    db: Session, resource_id: int, *, can_manage: bool
) -> Resource | None:
    """Retrieve a resource while enforcing catalogue visibility."""
    resource = db.get(Resource, resource_id)
    if resource is None:
        return None
    if not can_manage and (not resource.is_published or resource.is_archived):
        return None
    return resource
