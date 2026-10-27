"""Password reset API. Signed, purpose-bound links; no database migration needed."""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.email_service import send_notification_email
from app.utils.security import hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
EXPIRY_MINUTES = 20
GENERIC_MESSAGE = "If the email belongs to an active account, a password reset link will be sent."


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    new_password: str = Field(min_length=12, max_length=128)


def fingerprint(user: User) -> str:
    # The password hash is secret and salted; changing passwords rotates this value.
    return hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()


def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user.id),
            "purpose": "password_reset_v1",
            "pwd": fingerprint(user),
            "iat": now,
            "exp": now + timedelta(minutes=EXPIRY_MINUTES),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_payload(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "purpose", "pwd", "iat", "exp"]},
        )
        if payload.get("purpose") != "password_reset_v1":
            raise ValueError("Unexpected token purpose")
        return payload
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.") from exc


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is not None and user.is_active:
        # Never include the reset token in a log, exception, or API response.
        reset_url = "http://127.0.0.1:5500/reset-password.html?" + urlencode({"token": issue_token(user)})
        content = (
            "A password reset was requested for your UNN E-Library account.\n\n"
            f"Open this link to set a new password (valid for {EXPIRY_MINUTES} minutes):\n"
            f"{reset_url}\n\n"
            "If you didn't request this change, ignore this email. Your password is unchanged."
        )
        try:
            send_notification_email(recipient=user.email, subject="Reset your UNN E-Library password", body=content)
        except Exception:
            logger.exception("Password reset mail delivery failed for account id %s", user.id)
    return {"message": GENERIC_MESSAGE}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = get_payload(body.token)
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.") from exc
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or not user.is_active or fingerprint(user) != payload["pwd"]:
        db.rollback()
        raise HTTPException(400, "This reset link is invalid or has already been used.")
    user.password_hash = hash_password(body.new_password)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"message": "Password updated. Sign in with your new password."}
