
from sqlalchemy.orm import Session

from app.models.notification import Notification


def auth_headers(client, email):
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


def add_notification(db, user_id, visible=True):
    notification = Notification(
        user_id=user_id,
        title="New Academic Resource",
        message="A resource is available.",
        notification_type="new_resource",
        in_app_visible=visible,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification.id


def test_inbox_requires_authentication(client):
    assert client.get("/notifications").status_code == 401
    assert client.get(
        "/notifications/unread-count"
    ).status_code == 401


def test_user_can_read_own_notifications(
    client, student, test_engine
):
    with Session(test_engine) as db:
        add_notification(db, student)

    response = client.get(
        "/notifications",
        headers=auth_headers(client, "student@test.com"),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["unread_count"] == 1
    assert len(response.json()["items"]) == 1


def test_email_only_notification_is_hidden(
    client, student, test_engine
):
    with Session(test_engine) as db:
        add_notification(db, student, visible=False)

    headers = auth_headers(client, "student@test.com")

    inbox = client.get(
        "/notifications",
        headers=headers,
    )
    unread = client.get(
        "/notifications/unread-count",
        headers=headers,
    )

    assert inbox.status_code == 200
    assert inbox.json()["total"] == 0
    assert unread.json()["unread_count"] == 0


def test_user_can_mark_notification_as_read(
    client, student, test_engine
):
    with Session(test_engine) as db:
        notification_id = add_notification(db, student)

    headers = auth_headers(client, "student@test.com")

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert response.json()["read_at"] is not None

    unread = client.get(
        "/notifications/unread-count",
        headers=headers,
    )
    assert unread.json()["unread_count"] == 0


def test_user_cannot_read_another_users_notification(
    client, student, librarian, test_engine
):
    with Session(test_engine) as db:
        notification_id = add_notification(
            db, librarian
        )

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers=auth_headers(client, "student@test.com"),
    )

    assert response.status_code == 404


def test_user_can_update_preferences(client, student):
    headers = auth_headers(client, "student@test.com")

    response = client.patch(
        "/notifications/preferences",
        json={
            "new_resource_in_app": False,
            "new_resource_email": True,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "new_resource_in_app": False,
        "new_resource_email": True,
    }

    read_back = client.get(
        "/notifications/preferences",
        headers=headers,
    )

    assert read_back.status_code == 200
    assert read_back.json() == response.json()


def test_notification_preferences_reject_null(
    client, student
):
    response = client.patch(
        "/notifications/preferences",
        json={"new_resource_email": None},
        headers=auth_headers(client, "student@test.com"),
    )

    assert response.status_code == 400
