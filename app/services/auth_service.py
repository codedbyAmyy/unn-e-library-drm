from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.academic import Department
from app.schemas.auth import RegisterRequest
from app.utils.security import hash_password


def register_user(
    db: Session,
    user_data: RegisterRequest,
) -> User:
    """Create a new student or lecturer account."""
    email = str(user_data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise ValueError("An account with this email already exists.")

    # A valid department is required for both roles.
    if user_data.department_id is None:
        raise ValueError(
            "Students and lecturers must provide a department."
        )

    department = db.get(Department, user_data.department_id)

    if department is None:
        raise ValueError("The selected department does not exist.")

    if user_data.role == "student":
        if not user_data.matric_number:
            raise ValueError("Students must provide a matric number.")

        if not user_data.academic_level:
            raise ValueError("Students must provide an academic level.")

        if user_data.staff_id:
            raise ValueError("Students cannot provide a staff ID.")

        if user_data.academic_level not in {
            100, 200, 300, 400, 500, 600
        }:
            raise ValueError(
                "Academic level must be 100, 200, 300, 400, 500, or 600."
            )

    elif user_data.role == "lecturer":
        if not user_data.staff_id:
            raise ValueError("Lecturers must provide a staff ID.")

        if user_data.matric_number:
            raise ValueError("Lecturers cannot provide a matric number.")

        if user_data.academic_level is not None:
            raise ValueError("Lecturers cannot provide an academic level.")

    # Check matric number uniqueness.
    if user_data.matric_number:
        existing_matric = db.scalar(
            select(User).where(
                User.matric_number == user_data.matric_number
            )
        )

        if existing_matric:
            raise ValueError(
                "This matric number is already registered."
            )

    # Check staff ID uniqueness.
    if user_data.staff_id:
        existing_staff_id = db.scalar(
            select(User).where(
                User.staff_id == user_data.staff_id
            )
        )

        if existing_staff_id:
            raise ValueError(
                "This staff ID is already registered."
            )

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