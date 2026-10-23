
import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import hash_password


PASSWORD = "TestPassword123!"


def auth(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


@pytest.fixture
def admin(test_engine):
    with Session(test_engine) as db:
        user = User(
            full_name="Test Administrator",
            email="admin@test.com",
            password_hash=hash_password(PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        return user.id


def test_admin_can_list_users(
    client, admin, student, librarian
):
    response = client.get(
        "/admin/users",
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 3

    for user in response.json()["items"]:
        assert "password_hash" not in user
        assert "password" not in user


def test_admin_can_filter_users(
    client, admin, student, librarian
):
    response = client.get(
        "/admin/users?role=student",
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["role"] == "student"


def test_student_cannot_access_admin_users(
    client, student
):
    response = client.get(
        "/admin/users",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 403


def test_admin_can_deactivate_student(
    client, admin, student
):
    admin_auth = auth(client, "admin@test.com")

    response = client.patch(
        f"/admin/users/{student}/status",
        json={"is_active": False},
        headers=admin_auth,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False

    # The existing authentication dependency must reject the
    # student's previously issued token after deactivation.
    student_login = client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": PASSWORD,
        },
    )

    assert student_login.status_code == 403


def test_admin_can_reactivate_student(
    client, admin, student
):
    admin_auth = auth(client, "admin@test.com")

    disabled = client.patch(
        f"/admin/users/{student}/status",
        json={"is_active": False},
        headers=admin_auth,
    )
    assert disabled.status_code == 200

    enabled = client.patch(
        f"/admin/users/{student}/status",
        json={"is_active": True},
        headers=admin_auth,
    )

    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True


def test_admin_cannot_deactivate_self(
    client, admin
):
    response = client.patch(
        f"/admin/users/{admin}/status",
        json={"is_active": False},
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 403


def test_admin_cannot_change_own_role(
    client, admin
):
    response = client.patch(
        f"/admin/users/{admin}/role",
        json={"role": "librarian"},
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 403


def test_admin_can_assign_librarian_role(
    client, admin, student
):
    admin_auth = auth(client, "admin@test.com")

    response = client.patch(
        f"/admin/users/{student}/role",
        json={"role": "librarian"},
        headers=admin_auth,
    )

    assert response.status_code == 200, response.text
    assert response.json()["role"] == "librarian"

    # Existing JWT tokens containing the old student role
    # must be rejected by the authentication dependency.
    new_login = client.post(
        "/auth/login",
        json={
            "email": "student@test.com",
            "password": PASSWORD,
        },
    )
    assert new_login.status_code == 200

    me = client.get(
        "/auth/me",
        headers={
            "Authorization":
            f"Bearer {new_login.json()['access_token']}"
        },
    )
    assert me.status_code == 200
    assert me.json()["role"] == "librarian"


def test_student_cannot_change_user_role(
    client, student, librarian
):
    response = client.patch(
        f"/admin/users/{librarian}/role",
        json={"role": "student"},
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 403


def test_admin_cannot_promote_user_to_admin(
    client, admin, student
):
    response = client.patch(
        f"/admin/users/{student}/role",
        json={"role": "admin"},
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 422


def test_missing_user_returns_404(
    client, admin
):
    response = client.get(
        "/admin/users/999999",
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 404
def test_admin_cannot_demote_another_admin(
    client, admin, test_engine
):
    with Session(test_engine) as db:
        second_admin = User(
            full_name="Second Administrator",
            email="admin2@test.com",
            password_hash=hash_password(PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(second_admin)
        db.commit()
        second_admin_id = second_admin.id

    response = client.patch(
        f"/admin/users/{second_admin_id}/role",
        json={"role": "librarian"},
        headers=auth(client, "admin@test.com"),
    )

    assert response.status_code == 403

    with Session(test_engine) as db:
        saved = db.get(User, second_admin_id)
        assert saved.role == "admin"