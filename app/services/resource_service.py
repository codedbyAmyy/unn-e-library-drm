from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.academic import Course, Department
from app.models.resource import Category, Resource
from app.schemas.resource import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
)
from app.services.cas_service import queue_new_resource_notifications

def create_resource(
    db: Session,
    resource_data: ResourceCreateRequest,
    uploader_id: int,
) -> Resource:
    """Validate references and create an unpublished library resource"""
    data = resource_data.model_dump()
    
    #Validate the category
    if data["category_id"] is not None: 
        category = db.get(Category, data["category_id"])
        if category is None:
            raise ValueError("The selected category does not exist")
        
   # Validate the department, if given
    if data["department_id"] is not None:
        department = db.get(Department, data["department_id"])
        if department is None:
            raise ValueError("The selected department does not exist.")
        
    # Validate the course
    if data["course_id"] is not None:
        course = db.get(Course, data["course_id"])
        if course is None:
            raise ValueError("The selected course does not exist.")
        if (
            data["department_id"] is not None and course.department_id != data["department_id"]
        ):
            raise ValueError("The selected course does not belong to the selected department.")
        
        #If only a course is supplied, derive it's department
        if data["department_id"] is None:
            data["department_id"] = course.department_id
            
    resource = Resource(
        **data,
        uploaded_by=uploader_id,
        is_published=False,
        is_featured=False,
    )
    try:
        db.add(resource)
        db.commit()
        db.refresh(resource)
    except Exception:
        db.rollback()
        raise
    return resource

def update_resource(
    db: Session,
    resource_id: int,
    resource_data: ResourceUpdateRequest,
) -> Resource:
    """Update the supplied metadata of an existing library resource."""

    resource = db.get(Resource, resource_id)

    if resource is None:
        raise ValueError("Resource not found.")

    data = resource_data.model_dump(exclude_unset=True)

    # Validate the category, if supplied.
    if "category_id" in data and data["category_id"] is not None:
        if db.get(Category, data["category_id"]) is None:
            raise ValueError("The selected category does not exist.")

    # Validate the department, if supplied.
    if "department_id" in data and data["department_id"] is not None:
        if db.get(Department, data["department_id"]) is None:
            raise ValueError("The selected department does not exist.")

    # Validate the course, if supplied.
    if "course_id" in data and data["course_id"] is not None:
        course = db.get(Course, data["course_id"])

        if course is None:
            raise ValueError("The selected course does not exist.")

        effective_department_id = data.get(
            "department_id",
            resource.department_id,
        )

        if (
            effective_department_id is not None
            and course.department_id != effective_department_id
        ):
            raise ValueError(
                "The selected course does not belong to the selected department."
            )

    # If a course is supplied without a department, derive its department.
    if (
        data.get("course_id") is not None
        and "department_id" not in data
        and resource.department_id is None
    ):
        course = db.get(Course, data["course_id"])
        data["department_id"] = course.department_id

    try:
        for field, value in data.items():
            setattr(resource, field, value)

        db.commit()
        db.refresh(resource)

    except Exception:
        db.rollback()
        raise

    return resource

def publish_resource(
    db: Session,
    resource_id: int,
) -> Resource:
    """Publish an existing resource that has an uploaded PDF."""

    resource = db.get(Resource, resource_id)

    if resource is None:
        raise ValueError("Resource not found.")
    
    if resource.is_archived:
        raise ValueError("Archived resources must be restored before publishing.")

    if resource.is_published:
        raise ValueError("Resource is already published.")

    if not resource.files:
        raise ValueError(
            "A resource must have an uploaded PDF before publishing."
        )

    try:
        resource.is_published = True
        resource.published_at = datetime.now(timezone.utc)
        
        # Save publication and its CAS records together
        queue_new_resource_notifications(db, resource)

        db.commit()
        db.refresh(resource)

    except Exception:
        db.rollback()
        raise

    return resource

def unpublish_resource(
    db: Session,
    resource_id: int,
) -> Resource:
    """Unpublish an existing published library resource."""
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise ValueError("Resource not found.")
    if not resource.is_published:
        raise ValueError("Resource is already unpublished.")
    try:
        resource.is_published = False
        resource.published_at = None
        db.commit()
        db.refresh(resource)
    except Exception:
        db.rollback()
        raise
    return resource

def archive_resource(
    db: Session,
    resource_id: int,
) -> Resource:
    """Archive a resource without deleting its metadata or files."""
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise ValueError("Resource not found.")
    if resource.is_archived:
        raise ValueError("Resource is already published.")
    try:
        resource.is_archived = True
        resource.archived_at = datetime.now(timezone.utc)
        resource.is_published = False
        resource.published_at = None
        
        db.commit()
        db.refresh(resource)
    except Exception:
        db.rollback()
        raise
    return resource

def unarchive_resource(
    db: Session,
    resource_id: int,
) -> Resource:
    """Restore an archived resource to unpublished draft status."""
    resource = db.get(Resource, resource_id)
    
    if resource is None:
        raise ValueError("Resource not found.")
    if not resource.is_archived:
        raise ValueError("Resource is not archived.")
    
    try:
        resource.is_archived = False
        resource.archived_at = None
        resource.is_published = False
        resource.published_at = None
        
        db.commit()
        db.refresh(resource)
    except Exception:
        db.rollback()
        raise
    return resource