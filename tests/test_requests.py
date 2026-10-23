from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from sqlalchemy.orm import Session


def headers(client, email):
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


def request_payload():
    return {
        "title": "Advanced Database Systems",
        "author": "Sample Author",
        "resource_type": "book",
        "reason": "Needed for academic research.",
    }


def test_student_can_submit_and_view_request(client, student):
    auth = headers(client, "student@test.com")

    created = client.post(
        "/requests", json=request_payload(), headers=auth
    )

    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending"
    assert created.json()["requested_by"] == student

    listed = client.get("/requests", headers=auth)

    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_request_requires_authentication(client):
    assert client.get("/requests").status_code == 401
    assert client.post(
        "/requests", json=request_payload()
    ).status_code == 401


def test_librarian_cannot_submit_student_request(
    client, librarian
):
    response = client.post(
        "/requests",
        json=request_payload(),
        headers=headers(client, "librarian@test.com"),
    )
    assert response.status_code == 403


def test_student_can_cancel_pending_request(client, student):
    auth = headers(client, "student@test.com")
    created = client.post(
        "/requests", json=request_payload(), headers=auth
    )

    request_id = created.json()["id"]
    cancelled = client.post(
        f"/requests/{request_id}/cancel",
        headers=auth,
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_librarian_can_review_and_approve(
    client, student, librarian
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests",
        json=request_payload(),
        headers=student_auth,
    )
    request_id = created.json()["id"]

    reviewed = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "under_review"},
        headers=librarian_auth,
    )

    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "under_review"
    assert reviewed.json()["reviewed_by"] == librarian

    approved = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_rejection_requires_notes(client, student, librarian):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests", json=request_payload(),
        headers=student_auth,
    )
    request_id = created.json()["id"]

    rejected = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "rejected"},
        headers=librarian_auth,
    )

    assert rejected.status_code == 400


def test_student_cannot_review_request(client, student):
    auth = headers(client, "student@test.com")
    created = client.post(
        "/requests", json=request_payload(),
        headers=auth,
    )

    response = client.patch(
        f"/requests/{created.json()['id']}/review",
        json={"status": "approved"},
        headers=auth,
    )

    assert response.status_code == 403


def test_cancelled_request_cannot_be_approved(
    client, student, librarian
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests", json=request_payload(),
        headers=student_auth,
    )
    request_id = created.json()["id"]

    client.post(
        f"/requests/{request_id}/cancel",
        headers=student_auth,
    )

    response = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )

    assert response.status_code == 409

def test_librarian_can_list_student_requests(
    client, student, librarian
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests",
        json=request_payload(),
        headers=student_auth,
    )
    assert created.status_code == 201, created.text

    response = client.get(
        "/requests",
        headers=librarian_auth,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == created.json()["id"]

def test_student_cannot_cancel_another_students_request(
    client, student, test_engine
):
    from sqlalchemy.orm import Session

    from app.models.user import User
    from app.services.auth_service import hash_password

    # Create a second student using the existing test database.
    with Session(test_engine) as db:
        other_student = User(
            full_name="Second Test Student",
            email="second.student@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="student",
            is_active=True,
            department_id=None,
        )

        db.add(other_student)
        db.commit()

    owner_auth = headers(client, "student@test.com")
    other_auth = headers(client, "second.student@test.com")

    created = client.post(
        "/requests",
        json=request_payload(),
        headers=owner_auth,
    )

    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    # Another student cannot view the request.
    detail = client.get(
        f"/requests/{request_id}",
        headers=other_auth,
    )
    assert detail.status_code == 404

    # Another student cannot cancel the request.
    cancelled = client.post(
        f"/requests/{request_id}/cancel",
        headers=other_auth,
    )
    assert cancelled.status_code == 404

    # The original student still owns the pending request.
    owner_detail = client.get(
        f"/requests/{request_id}",
        headers=owner_auth,
    )
    assert owner_detail.status_code == 200
    assert owner_detail.json()["status"] == "pending"

def test_approved_request_requires_published_resource_to_fulfil(
    client, student, librarian
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests",
        json=request_payload(),
        headers=student_auth,
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    approved = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )
    assert approved.status_code == 200, approved.text

    no_resource = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "fulfilled"},
        headers=librarian_auth,
    )
    assert no_resource.status_code == 400

    missing_resource = client.patch(
        f"/requests/{request_id}/review",
        json={
            "status": "fulfilled",
            "fulfilled_resource_id": 999999,
        },
        headers=librarian_auth,
    )
    assert missing_resource.status_code == 400

    detail = client.get(
        f"/requests/{request_id}",
        headers=student_auth,
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "approved"


def test_rejected_request_cannot_be_reviewed_again(
    client, student, librarian
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    created = client.post(
        "/requests",
        json=request_payload(),
        headers=student_auth,
    )
    assert created.status_code == 201, created.text

    request_id = created.json()["id"]

    rejected = client.patch(
        f"/requests/{request_id}/review",
        json={
            "status": "rejected",
            "review_notes": "Material cannot be acquired.",
        },
        headers=librarian_auth,
    )
    assert rejected.status_code == 200, rejected.text

    reviewed_again = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )
    assert reviewed_again.status_code == 409

def test_librarian_can_fulfil_approved_request(
    client, student, librarian, test_engine
):
    student_auth = headers(client, "student@test.com")
    librarian_auth = headers(client, "librarian@test.com")

    # 1. Student submits a resource request.
    created = client.post(
        "/requests",
        json=request_payload(),
        headers=student_auth,
    )

    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    # 2. Librarian approves the request.
    approved = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )

    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    # 3. Create a published resource in the TEST database.
    # This avoids uploading a real PDF to Supabase.
    with Session(test_engine) as db:
        resource = Resource(
            title="Advanced Database Systems",
            resource_type="book",
            uploaded_by=librarian,
            is_published=True,
            is_archived=False,
            published_at=datetime.now(timezone.utc),
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        resource_id = resource.id

    # 4. Librarian fulfils the approved request.
    fulfilled = client.patch(
        f"/requests/{request_id}/review",
        json={
            "status": "fulfilled",
            "fulfilled_resource_id": resource_id,
            "review_notes": "The requested resource is available.",
        },
        headers=librarian_auth,
    )

    assert fulfilled.status_code == 200, fulfilled.text

    result = fulfilled.json()

    assert result["status"] == "fulfilled"
    assert result["fulfilled_resource_id"] == resource_id
    assert result["reviewed_by"] == librarian
    assert result["reviewed_at"] is not None

    # 5. Student can see the fulfilled request.
    detail = client.get(
        f"/requests/{request_id}",
        headers=student_auth,
    )

    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "fulfilled"
    assert detail.json()["fulfilled_resource_id"] == resource_id

    # 6. Confirm the changes were saved in PostgreSQL.
    with Session(test_engine) as db:
        saved_request = db.get(ResourceRequest, request_id)

        assert saved_request is not None
        assert saved_request.status == "fulfilled"
        assert saved_request.fulfilled_resource_id == resource_id

    # 7. A fulfilled request cannot be reviewed again.
    repeated_review = client.patch(
        f"/requests/{request_id}/review",
        json={"status": "approved"},
        headers=librarian_auth,
    )

    assert repeated_review.status_code == 409
