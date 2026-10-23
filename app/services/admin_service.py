from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User

def admin_error(
    status_code: int,
    message: str,
):
    raise HTTPException(
        status_code=status_code,
        detail=message,
    )
    
def list_users(
    db: Session,
    *,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    filters = []
    
    if role is not None:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active.is_(is_active))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.matric_number.ilike(pattern),
                User.staff_id.ilike(pattern),
            )
        )
        
    total = db.scalar(
        select(func.count(User.id)).where(*filters)
    ) or 0
    
    users = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return users, total

def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    
    if user is None:
        admin_error(404, "User not found.")
    return user

def update_user_status(
    db: Session,
    *,
    user_id: int,
    admin_id: int,
    is_active: bool,
) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )
    
    if user is None:
        admin_error(404, "User not found.")
    if user.id == admin_id:
        admin_error(403, "Administrators cannot change their own account status.")
        
    # Protect other administrator accounts as well.
    if user.role == "admin":
        admin_error(403, "Administrator account status cannot be changed here.")
    if user.is_active == is_active:
        admin_error(409, "Account already has the requested status.")
        
    try:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user

def update_user_role(
    db: Session,
    *,
    user_id: int,
    admin_id: int,
    new_role: str,
) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )
    if user is None:
        admin_error(404, "User not found.")
    if user.id == admin_id:
        admin_error(403, "Administrators cannot change their own role.")
    if user.role == "admin" or new_role == "admin":
        admin_error(403, "Administrator role changes require a seperate privileged provisioning process.")
    if user.role == new_role:
        admin_error(409, "User already has the requested role.")
        
    #Preserve the academic identity rules used at registration.
    if new_role == "student":
        if (
            user.department_id is None
            or not user.matric_number
            or user.academic_level not in {
                100, 200, 300, 400, 500, 600
            }
            or user.staff_id is not None
        ):
            admin_error(400, "Account does not have valid student academic details.")
    elif new_role == "lecturer":
        if (
            user.department_id is None
            or not user.staff_id
            or user.matric_number is not None
            or user.academic_level is not None
        ):
            admin_error(400, "Account does not have valid lecturer academic details.")
    elif new_role != "librarian":
        admin_error(400, "Invalid target role.")
        
    try:
        user.role = new_role
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user