from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

import pytest

def student_payload(department_id=None):
    return {
        "full_name": "Test Student",
        "email": "student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "2026/250100",
        "department_id": department_id,
        "academic_level": 300,
    }


def test_successful_registration(client, test_engine, test_department):
    response = client.post(
        "/auth/register",
        json=student_payload(test_department),
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


def test_duplicate_email_is_rejected(client, test_department):
    payload = student_payload(test_department)

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


def test_student_must_provide_matric_number(client, test_department):
    payload = student_payload(test_department)
    payload["email"] = "another.student@example.com"
    payload.pop("matric_number")

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert "matric number" in response.json()["detail"]

@pytest.mark.parametrize(
    "matric_number",
    [
        "22/250100",       # Admission year too short
        "2022-250100",     # Wrong separator
        "2022/25010",      # Only five digits after slash
        "2022/2501000",    # Seven digits after slash
        "ABCD/250100",     # Letters instead of year digits
        "2022/25A100",     # Letter inside matric number
    ],
)
def test_invalid_matric_number_is_rejected(client, matric_number):
    payload = student_payload()
    payload["email"] = "invalid.matric@example.com"
    payload["matric_number"] = matric_number

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 422
