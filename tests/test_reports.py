
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.report import BrokenResourceReport
from app.models.resource import Resource
from app.models.user import User
from app.utils.security import hash_password


PASSWORD = "TestPassword123!"


def auth(client, email):
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
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
    published=True,
    archived=False,
):
    with Session(test_engine) as db:
        resource = Resource(
            title="Testing Broken Resource Reports",
            resource_type="book",
            uploaded_by=librarian_id,
            is_published=published,
            is_archived=archived,
            published_at=(
                datetime.now(timezone.utc)
                if published else None
            ),
        )

        db.add(resource)
        db.commit()

        return resource.id


def report_payload(resource_id):
    return {
        "resource_id": resource_id,
        "issue_type": "file_unavailable",
        "description": "The PDF does not open.",
    }


def test_student_can_report_resource(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    response = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 201, response.text

    data = response.json()
    assert data["resource_id"] == resource_id
    assert data["reported_by"] == student
    assert data["status"] == "open"
    assert data["reviewed_by"] is None


def test_student_can_list_own_reports(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    student_auth = auth(client, "student@test.com")

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=student_auth,
    )
    assert created.status_code == 201, created.text

    listing = client.get(
        "/reports",
        headers=student_auth,
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == (
        created.json()["id"]
    )


def test_librarian_can_view_reports(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )
    assert created.status_code == 201, created.text

    listing = client.get(
        "/reports",
        headers=auth(client, "librarian@test.com"),
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_librarian_can_resolve_report(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    assert created.status_code == 201, created.text
    report_id = created.json()["id"]

    reviewed = client.patch(
        f"/reports/{report_id}/review",
        json={
            "status": "under_review",
        },
        headers=auth(client, "librarian@test.com"),
    )

    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "under_review"

    resolved = client.patch(
        f"/reports/{report_id}/review",
        json={
            "status": "resolved",
            "resolution_notes": (
                "The PDF file was replaced."
            ),
        },
        headers=auth(client, "librarian@test.com"),
    )

    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["reviewed_by"] == librarian
    assert resolved.json()["resolved_at"] is not None

    with Session(test_engine) as db:
        saved = db.get(BrokenResourceReport, report_id)
        assert saved is not None
        assert saved.status == "resolved"


def test_student_cannot_review_report(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    response = client.patch(
        f"/reports/{created.json()['id']}/review",
        json={
            "status": "resolved",
            "resolution_notes": "Fixed",
        },
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 403


def test_resolution_requires_notes(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    response = client.patch(
        f"/reports/{created.json()['id']}/review",
        json={"status": "resolved"},
        headers=auth(client, "librarian@test.com"),
    )

    assert response.status_code == 400


def test_closed_report_cannot_be_reviewed_again(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    report_id = created.json()["id"]
    librarian_auth = auth(client, "librarian@test.com")

    closed = client.patch(
        f"/reports/{report_id}/review",
        json={
            "status": "dismissed",
            "resolution_notes": "The resource is accessible.",
        },
        headers=librarian_auth,
    )

    assert closed.status_code == 200, closed.text

    second_review = client.patch(
        f"/reports/{report_id}/review",
        json={
            "status": "under_review",
        },
        headers=librarian_auth,
    )

    assert second_review.status_code == 409


def test_cannot_report_archived_resource(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine,
        librarian,
        archived=True,
    )

    response = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 404


def test_cannot_report_unpublished_resource(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine,
        librarian,
        published=False,
    )

    response = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 404


def test_other_issue_requires_description(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    response = client.post(
        "/reports",
        json={
            "resource_id": resource_id,
            "issue_type": "other",
        },
        headers=auth(client, "student@test.com"),
    )

    assert response.status_code == 422


def test_student_cannot_view_another_students_report(
    client, student, librarian, test_engine
):
    resource_id = make_resource(
        test_engine, librarian
    )

    with Session(test_engine) as db:
        second_student = User(
            full_name="Second Student",
            email="second.student@test.com",
            password_hash=hash_password(PASSWORD),
            role="student",
            matric_number="2026/250101",
            department_id=None,
            academic_level=300,
            is_active=True,
        )

        db.add(second_student)
        db.commit()

    created = client.post(
        "/reports",
        json=report_payload(resource_id),
        headers=auth(client, "student@test.com"),
    )
    assert created.status_code == 201, created.text

    other_auth = auth(
        client, "second.student@test.com"
    )

    report_id = created.json()["id"]

    detail = client.get(
        f"/reports/{report_id}",
        headers=other_auth,
    )

    assert detail.status_code == 404

    listing = client.get(
        "/reports",
        headers=other_auth,
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 0
