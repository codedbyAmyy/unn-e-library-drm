
import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)


def test_valid_student_registration():
    user = RegisterRequest(
        full_name="Test Student",
        email="student@example.com",
        password="StrongPassword123!",
        role="student",
        matric_number="TEST/2026/001",
    )

    assert user.role == "student"
    assert user.email == "student@example.com"


def test_registration_rejects_admin_role():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Admin",
            email="admin@example.com",
            password="StrongPassword123!",
            role="admin",
        )


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="student@example.com",
            password="short",
            role="student",
        )


def test_login_schema():
    login = LoginRequest(
        email="student@example.com",
        password="any-existing-password",
    )

    assert login.email == "student@example.com"


def test_token_response():
    token = TokenResponse(access_token="test-token")

    assert token.access_token == "test-token"
    assert token.token_type == "bearer"
