
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.tokens import decode_access_token


def student_payload(department_id):
    return {
        "full_name": "Login Test Student",
        "email": "login.student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "2026/250101",
        "department_id": department_id,
        "academic_level": 300,
    }


def test_successful_login_returns_access_token(client, test_engine, test_department):
    registration = client.post(
        "/auth/register",
        json=student_payload(test_department),
    )
    assert registration.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": "login.student@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]

    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(registration.json()["id"])
    assert payload["role"] == "student"

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(
                User.email == "login.student@example.com"
            )
        )
        assert user.last_login_at is not None


def test_login_rejects_wrong_password(client, test_department):
    client.post("/auth/register", json=student_payload(test_department))

    response = client.post(
        "/auth/login",
        json={
            "email": "login.student@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_inactive_account(client, test_engine, test_department):
    client.post("/auth/register", json=student_payload(test_department))

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(
                User.email == "login.student@example.com"
            )
        )
        user.is_active = False
        db.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "login.student@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This account is inactive."
