
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def student_payload(department_id):
    return {
        "full_name": "Profile Test Student",
        "email": "profile.student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "2026/250100",
        "department_id": department_id,
        "academic_level": 300
    }


def register_and_login(client, test_department):
    registration = client.post(
        "/auth/register",
        json=student_payload(test_department),
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "profile.student@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_user_can_update_own_full_name(client, test_engine, test_department):
    headers = register_and_login(client, test_department)

    response = client.patch(
        "/auth/me",
        json={"full_name": "Updated Student Name"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Student Name"

    with Session(test_engine) as db:
        user = db.scalar(
            select(User).where(
                User.email == "profile.student@example.com"
            )
        )
        assert user.full_name == "Updated Student Name"


def test_profile_update_requires_authentication(client):
    response = client.patch(
        "/auth/me",
        json={"full_name": "Updated Student Name"},
    )

    assert response.status_code == 401


def test_profile_update_rejects_short_name(client, test_department):
    headers = register_and_login(client, test_department)

    response = client.patch(
        "/auth/me",
        json={"full_name": "A"},
        headers=headers,
    )

    assert response.status_code == 422


def test_profile_update_does_not_allow_role_change(client, test_department):
    headers = register_and_login(client, test_department)

    response = client.patch(
        "/auth/me",
        json={
            "full_name": "Profile Test Student",
            "role": "admin",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "student"


def test_profile_update_does_not_allow_account_status_change(client, test_department):
    headers = register_and_login(client, test_department)

    response = client.patch(
        "/auth/me",
        json={
            "full_name": "Profile Test Student",
            "is_active": False,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_profile_update_rejects_empty_request(client, test_department):
    headers = register_and_login(client, test_department)

    response = client.patch(
        "/auth/me",
        json={},
        headers=headers,
    )

    assert response.status_code == 422
