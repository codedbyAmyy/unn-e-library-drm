from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
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
    for field, value in updates.items():
        setattr(current_user, field, value)      
    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
            db.rollback()
            raise
    return current_user