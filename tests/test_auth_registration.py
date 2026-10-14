
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def student_payload():
    return {
        "full_name": "Test Student",
        "email": "student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "TEST/2026/001",
    }


def test_successful_registration(client, test_engine):
    response = client.post(
        "/auth/register",
        json=student_payload(),
    )

    assert response.status_code == 201
    assert response.json()["email"] == "student@example.com"
    assert response.json()["role"] == "student"
    assert "password_hash" not in response.json()

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(User.email == "student@example.com")
        )

        assert user is not None
        assert user.password_hash != "StrongPassword123!"
        assert user.password_hash.startswith("$argon2")


def test_duplicate_email_is_rejected(client):
    payload = student_payload()

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert "already exists" in second_response.json()["detail"]


def test_registration_rejects_admin_role(client):
    payload = student_payload()
    payload["email"] = "admin@example.com"
    payload["role"] = "admin"

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422


def test_student_must_provide_matric_number(client):
    payload = student_payload()
    payload["email"] = "another.student@example.com"
    payload.pop("matric_number")

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert "matric number" in response.json()["detail"]
