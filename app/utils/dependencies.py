from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.tokens import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate the access token and return the authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        token_role = payload.get("role")
        
        if user_id <= 0 or not token_role:
            raise credentials_exception
    
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise credentials_exception from exc
    
    user = db.scalar(
        select(User).where(User.id == user_id)
    )
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    # Do not trust a stale role claim if the user's role changed 
    if user.role != token_role:
        raise credentials_exception
    
    return user

def require_roles(*allowed_roles: str):
    """Restrict an endpoint to the specified user roles"""
    
    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User: 
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )
            
        return current_user
    
    return role_checker