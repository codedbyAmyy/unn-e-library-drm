from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.utils.security import hash_password

def register_user(
    db: Session,
    user_data: RegisterRequest,
) -> User:
    """Create a new student or lecturer account"""
    email = str(user_data.email).strip().lower()
    
    existing_user = db.scalar(
        select(User).where(User.email == email)
    )
    
    if existing_user:
        raise ValueError("An account with this email already exists")
    
    if user_data.role == "student":
        if not user_data.matric_number:
            raise ValueError("Students must provide a matric number.")
        if user_data.staff_id:
            raise ValueError("Students cannot provide a staff ID.")
        
    if user_data.role == "lecturer":
        if not user_data.staff_id:
            raise ValueError("Lecturers must provide a staff ID")
        if user_data.matric_number:
            raise ValueError("Lecturers cannot provide a matric number")
        if user_data.academic_level is not None:
            raise ValueError("Lecturers cannot provide an academic level")
        
    if user_data.matric_number:
        existing_matric = db.scalar(
            select(User).where(
                User.matric_number == user_data.matric_number
            )
        )
        if existing_matric:
            raise ValueError("This matric number is already registered.")
    
    user = User(
        full_name=user_data.full_name.strip(),
        email=email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        matric_number=user_data.matric_number,
        staff_id=user_data.staff_id,
        department_id=user_data.department_id,
        academic_level=user_data.academic_level,
    )
    
    db.add(user)
    
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    
    return user