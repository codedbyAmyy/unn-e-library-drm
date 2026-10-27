from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from app.models.academic import Department
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import(
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ProfileUpdateRequest,
    ) 
from app.services.auth_service import register_user
from app.utils.security import verify_password
from app.utils.tokens import create_access_token
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        return register_user(db, user_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with the supplied details already exists."
        ) from exc
        
@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data:LoginRequest,
    db: Session = Depends(get_db),
):
    email = str(login_data.email).strip().lower()
    
    user = db.scalar(
        select(User).where(User.email == email)
    )
    
    if user is None or not verify_password(
        login_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    user.last_login_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )
    
    return TokenResponse(access_token=access_token)

@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=True,
)
def swagger_login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    db: Session = Depends(get_db),
):
    """OAuth2-compatible login for Swagger documentation.

    Use the librarian's email in the username field.
    The regular JSON login remains available at /auth/login.
    """
    login_data = LoginRequest(
        email=form_data.username,
        password=form_data.password,
    )

    return login(
        login_data=login_data,
        db=db,
    )

@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return the profile of the authenticated user."""
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    profile_data: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Update permitted fields in the authenticated user's profile."""
    updates = profile_data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile changes were provided."
        )
    # Role and email are not editable through this endpoint.
    if ("department_id" in updates or "academic_level" in updates) and current_user.role not in ("student", "lecturer"):
        raise HTTPException(status_code=403, detail="Academic affiliation cannot be changed for this role.")

    if "department_id" in updates and updates["department_id"] is not None:
        if db.get(Department, updates["department_id"]) is None:
            raise HTTPException(status_code=422, detail="Choose a valid department.")

    if "full_name" in updates:
        if updates["full_name"] is None or not updates["full_name"].strip():
            raise HTTPException(status_code=422, detail="Full name cannot be blank.")
        updates["full_name"] = updates["full_name"].strip()

    for field, value in updates.items():
        setattr(current_user, field, value)      
    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
            db.rollback()
            raise
    return current_user