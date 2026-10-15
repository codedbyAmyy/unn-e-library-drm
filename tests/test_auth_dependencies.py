from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.utils.dependencies import require_roles

def student_payload(department_id):
    return {
        "full_name": "Security Test Student",
        "email": "security.student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "2026/250100",
        "department_id": department_id,
        "academic_level": 300,
    }


def register_and_login(client, department_id):
    registration = client.post(
        "/auth/register",
        json=student_payload(department_id),
    )
    assert registration.status_code == 201, registration.json()

    login = client.post(
        "/auth/login",
        json={
            "email": "security.student@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login.status_code == 200, login.json()

    return login.json()["access_token"]


def test_authenticated_user_can_view_own_profile(client, test_department):
    token = register_and_login(client, test_department)

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "security.student@example.com"
    assert response.json()["role"] == "student"
    assert "password_hash" not in response.json()


def test_profile_rejects_missing_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_profile_rejects_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_profile_rejects_expired_token(client):
    now = datetime.now(timezone.utc)

    expired_token = jwt.encode(
        {
            "sub": "1",
            "role": "student",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_profile_rejects_inactive_user(client, test_engine, test_department):
    token = register_and_login(client, test_department)

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(
                User.email == "security.student@example.com"
            )
        )
        user.is_active = False
        db.commit()

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_profile_rejects_token_after_role_changes(client, test_engine, test_department):
    token = register_and_login(client, test_department)

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(
                User.email == "security.student@example.com"
            )
        )
        user.role = "lecturer"
        db.commit()

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401

def test_librarian_role_is_allowed():
    checker = require_roles("librarian")
    user = SimpleNamespace(role="librarian")

    result = checker(current_user=user)

    assert result is user


def test_student_is_forbidden_from_librarian_only_access():
    checker = require_roles("librarian")
    user = SimpleNamespace(role="student")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=user)

    assert exc_info.value.status_code == 403