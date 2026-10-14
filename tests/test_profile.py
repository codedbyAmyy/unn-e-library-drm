
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def student_payload():
    return {
        "full_name": "Profile Test Student",
        "email": "profile.student@example.com",
        "password": "StrongPassword123!",
        "role": "student",
        "matric_number": "PROFILE/2026/001",
    }


def register_and_login(client):
    registration = client.post(
        "/auth/register",
        json=student_payload(),
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


def test_user_can_update_own_full_name(client, test_engine):
    headers = register_and_login(client)

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


def test_profile_update_rejects_short_name(client):
    headers = register_and_login(client)

    response = client.patch(
        "/auth/me",
        json={"full_name": "A"},
        headers=headers,
    )

    assert response.status_code == 422


def test_profile_update_does_not_allow_role_change(client):
    headers = register_and_login(client)

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


def test_profile_update_does_not_allow_account_status_change(client):
    headers = register_and_login(client)

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


def test_profile_update_rejects_empty_request(client):
    headers = register_and_login(client)

    response = client.patch(
        "/auth/me",
        json={},
        headers=headers,
    )

    assert response.status_code == 422
