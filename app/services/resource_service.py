from sqlalchemy.orm import Session

from app.models.academic import Course, Department
from app.models.resource import Category, Resource
from app.schemas.resource import ResourceCreateRequest

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
        