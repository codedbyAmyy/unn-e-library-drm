"""Read-only academic selectors for existing departments and courses."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.academic import Course, Department
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/academic", tags=["Academic Lookups"])

@router.get("/departments")
def departments(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    rows = db.scalars(select(Department).order_by(Department.name)).all()
    return [{"id": x.id, "name": x.name, "code": x.code} for x in rows]

@router.get("/courses")
def courses(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)], department_id: Annotated[int | None, Query(gt=0)] = None):
    query = select(Course).order_by(Course.course_code)
    if department_id is not None:
        query = query.where(Course.department_id == department_id)
    rows = db.scalars(query).all()
    return [{"id": x.id, "title": x.title, "course_code": x.course_code, "department_id": x.department_id, "academic_level": x.academic_level} for x in rows]
