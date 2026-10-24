from unittest.mock import patch
from sqlalchemy.orm import Session

from app.models.reading import ReadingHistory
from app.models.resource import Resource
from app.models.user import User
from app.services.personalization_service import (
    record_successful_read,
)

PASSWORD = "TestPassword123!"


def auth(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text

    return {
        "Authorization":
        f"Bearer {response.json()['access_token']}"
    }


def make_resource(
    test_engine,
    librarian_id,
    *,
    title="Computer Science Textbook",
    department_id=None,
    category_id=None,
    published=True,
    archived=False,
):
    with Session(test_engine) as db:
        resource = Resource(
            title=title,
            resource_type="book",
            department_id=department_id,
            category_id=category_id,
            uploaded_by=librarian_id,
            is_published=published,
            is_archived=archived,
        )
        db.add(resource)
        db.commit()
        return resource.id


def test_student_can_bookmark_resource(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)

    response = client.post(
        f"/bookmarks/{resource_id}",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["resource_id"] == resource_id
    assert response.json()["user_id"] == student


def test_duplicate_bookmark_is_rejected(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)
    headers = auth(client, "student@test.com")

    first = client.post(
        f"/bookmarks/{resource_id}", headers=headers
    )
    second = client.post(
        f"/bookmarks/{resource_id}", headers=headers
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_student_can_remove_bookmark(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)
    headers = auth(client, "student@test.com")

    client.post(f"/bookmarks/{resource_id}", headers=headers)

    response = client.delete(
        f"/bookmarks/{resource_id}", headers=headers
    )

    assert response.status_code == 204

    listing = client.get("/bookmarks", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_unpublished_resource_cannot_be_bookmarked(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian, published=False
    )

    response = client.post(
        f"/bookmarks/{resource_id}",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 404


def test_archived_resource_cannot_be_bookmarked(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian, archived=True
    )

    response = client.post(
        f"/bookmarks/{resource_id}",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 404


def test_reading_history_is_persisted(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)

    with Session(test_engine) as db:
        record_successful_read(
            db,
            user_id=student,
            resource_id=resource_id,
        )

        count = db.query(ReadingHistory).count()
        assert count == 1

    response = client.get(
        "/reading-history",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["resource_id"] == (
        resource_id
    )
    assert response.json()["items"][0]["duration_seconds"] == 0


def test_recommendations_exclude_unpublished_and_archived(
    client, student, librarian, test_engine
):
    visible_id = make_resource(
        test_engine,
        librarian,
        title="Visible Resource",
    )
    hidden_id = make_resource(
        test_engine,
        librarian,
        title="Hidden Resource",
        published=False,
    )
    archived_id = make_resource(
        test_engine,
        librarian,
        title="Archived Resource",
        archived=True,
    )

    response = client.get(
        "/recommendations/me",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 200, response.text

    ids = {
        item["resource"]["id"]
        for item in response.json()["items"]
    }

    assert visible_id in ids
    assert hidden_id not in ids
    assert archived_id not in ids


def test_read_resources_are_excluded_from_recommendations(
    client, student, librarian, test_engine
):
    read_id = make_resource(
        test_engine,
        librarian,
        title="Already Read",
    )
    unread_id = make_resource(
        test_engine,
        librarian,
        title="Not Yet Read",
    )

    with Session(test_engine) as db:
        record_successful_read(
            db,
            user_id=student,
            resource_id=read_id,
        )

    response = client.get(
        "/recommendations/me",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 200, response.text

    ids = {
        item["resource"]["id"]
        for item in response.json()["items"]
    }

    assert read_id not in ids
    assert unread_id in ids


def test_matching_department_gets_higher_score(
    client, student, librarian, test_engine
):
    with Session(test_engine) as db:
        student_user = db.get(User, student)
        department_id = student_user.department_id

    # The existing student fixture should belong to a department.
    assert department_id is not None

    matching_id = make_resource(
        test_engine,
        librarian,
        title="Department-specific book",
        department_id=department_id,
    )
    general_id = make_resource(
        test_engine,
        librarian,
        title="General library book",
    )

    response = client.get(
        "/recommendations/me",
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 200, response.text

    scores = {
        item["resource"]["id"]: item["score"]
        for item in response.json()["items"]
    }

    assert scores[matching_id] > scores[general_id]


def test_bookmarks_are_private(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)

    student_auth = auth(client, "student@test.com")
    librarian_auth = auth(client, "librarian@test.com")

    saved = client.post(
        f"/bookmarks/{resource_id}",
        headers=student_auth,
    )
    assert saved.status_code == 201

    other_listing = client.get(
        "/bookmarks",
        headers=librarian_auth,
    )

    assert other_listing.status_code == 200
    assert other_listing.json()["total"] == 0

def test_successful_drm_read_records_history(
    client, student, librarian, test_engine
):
    resource_id = make_resource(test_engine, librarian)
    headers = auth(client, "student@test.com")

    with patch(
        "app.routers.resources.get_protected_pdf",
        return_value=b"%PDF-1.4\nTest PDF",
    ):
        response = client.get(
            f"/resources/{resource_id}/read",
            headers=headers,
        )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"

    history = client.get(
        "/reading-history",
        headers=headers,
    )

    assert history.status_code == 200, history.text
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["resource_id"] == resource_id


def test_failed_drm_read_does_not_record_history(
    client, student, librarian, test_engine
):
    from app.services.drm_service import DRMAccessError

    resource_id = make_resource(test_engine, librarian)
    headers = auth(client, "student@test.com")

    with patch(
        "app.routers.resources.get_protected_pdf",
        side_effect=DRMAccessError(
            status_code=403,
            detail="Access denied.",
        ),
    ):
        response = client.get(
            f"/resources/{resource_id}/read",
            headers=headers,
        )

    assert response.status_code == 403

    history = client.get(
        "/reading-history",
        headers=headers,
    )

    assert history.status_code == 200
    assert history.json()["total"] == 0