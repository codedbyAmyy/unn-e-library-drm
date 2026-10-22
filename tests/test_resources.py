import pytest
from unittest.mock import patch
from types import SimpleNamespace
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.academic import Course
from app.utils.security import hash_password


@pytest.fixture
def librarian(test_engine, test_department):
    with Session(test_engine) as db:
        user = User(
            full_name="Test Librarian",
            email="librarian@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="librarian",
            department_id=test_department,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        librarian_id = user.id

    return librarian_id


@pytest.fixture
def student(test_engine, test_department):
    with Session(test_engine) as db:
        user = User(
            full_name="Test Student",
            email="student@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="student",
            matric_number="2026/250100",
            department_id=test_department,
            academic_level=300,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        student_id = user.id

    return student_id


def test_resources_endpoint_is_registered(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/resources" in response.json()["paths"]

def login_and_get_token(client, email, password="TestPassword123!"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def resource_payload(**overrides):
    payload = {
        "title": "Introduction to Computer Science",
        "abstract": "A test resource for the university e-library.",
        "resource_type": "book",
        "publication_year": 2024,
        "publisher": "Test University Press",
        "language": "English",
    }
    payload.update(overrides)
    return payload


def test_librarian_can_create_resource(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Introduction to Computer Science"
    assert data["uploaded_by"] == librarian
    assert data["is_published"] is False
    assert data["is_featured"] is False


def test_student_cannot_create_resource(
    client, student
):
    token = login_and_get_token(client, "student@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to perform this action."
    )


def test_unauthenticated_user_cannot_create_resource(client):
    response = client.post(
        "/resources",
        json=resource_payload(),
    )

    assert response.status_code == 401

def test_resource_rejects_nonexistent_category(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(category_id=999999),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected category does not exist"
    )


def test_resource_rejects_nonexistent_department(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(department_id=999999),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected department does not exist."
    )


def test_resource_rejects_nonexistent_course(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(course_id=999999),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected course does not exist."
    )

def test_resource_rejects_course_from_another_department(
    client, librarian, test_engine, test_department
):
    with Session(test_engine) as db:
        course = Course(
            department_id=test_department,
            course_code="CSC301",
            title="Data Structures",
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        course_id = course.id

    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(
            course_id=course_id,
            department_id=999999,
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected department does not exist."
    )


def test_resource_uses_course_department_when_omitted(
    client, librarian, test_engine, test_department
):
    with Session(test_engine) as db:
        course = Course(
            department_id=test_department,
            course_code="CSC302",
            title="Database Systems",
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        course_id = course.id

    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        "/resources",
        json=resource_payload(course_id=course_id),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["course_id"] == course_id
    assert response.json()["department_id"] == test_department

def test_resource_rejects_duplicate_isbn(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        "/resources",
        json=resource_payload(
            isbn="9780131103627",
            department_id=test_department,
        ),
        headers=headers,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/resources",
        json=resource_payload(
            title="Another Book",
            isbn="9780131103627",
            department_id=test_department,
        ),
        headers=headers,
    )

    assert second_response.status_code == 409


def test_resource_rejects_duplicate_doi(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        "/resources",
        json=resource_payload(
            doi="10.1234/test-resource",
            department_id=test_department,
        ),
        headers=headers,
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/resources",
        json=resource_payload(
            title="Another Research Paper",
            doi="10.1234/test-resource",
            department_id=test_department,
        ),
        headers=headers,
    )

    assert second_response.status_code == 409

def test_resource_file_upload_endpoint_is_registered(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/resources/{resource_id}/files" in response.json()["paths"]


def test_student_cannot_upload_resource_file(
    client, student, librarian, test_department
):
    # Create a resource first.
    librarian_token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers={
            "Authorization": f"Bearer {librarian_token}"
        },
    )
    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    student_token = login_and_get_token(
        client, "student@test.com"
    )

    response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
        headers={
            "Authorization": f"Bearer {student_token}"
        },
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_upload_resource_file(
    client, librarian, test_department
):
    # Create a resource first.
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 401

@patch("app.services.storage_service.upload_resource_file")
def test_librarian_can_upload_resource_file(
    mock_upload,
    client,
    librarian,
    test_department,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(
            department_id=test_department
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    pdf_content = b"%PDF-1.7\nTest PDF content"

    response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "lecture-notes.pdf",
                pdf_content,
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["message"] == (
        "Resource file uploaded successfully."
    )
    assert data["file"]["resource_id"] == resource_id
    assert data["file"]["original_filename"] == (
        "lecture-notes.pdf"
    )
    assert data["file"]["mime_type"] == "application/pdf"
    assert data["file"]["file_size_bytes"] == len(pdf_content)
    assert len(data["file"]["checksum_sha256"]) == 64

    mock_upload.assert_called_once()

@patch("app.services.storage_service.supabase")
def test_librarian_cannot_upload_non_pdf_file(
    mock_supabase,
    client,
    librarian,
    test_department,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(
            department_id=test_department
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "notes.txt",
                b"This is not a PDF",
                "text/plain",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only PDF files are allowed."
    )

    mock_supabase.storage.from_.return_value.upload.assert_not_called()


@patch("app.services.storage_service.supabase")
def test_upload_rejects_nonexistent_resource(
    mock_supabase,
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    response = client.post(
        "/resources/999999/files",
        files={
            "file": (
                "notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected resource does not exist."
    )

    mock_supabase.storage.from_.return_value.upload.assert_not_called()


@patch("app.services.storage_service.supabase")
def test_librarian_cannot_upload_oversized_file(
    mock_supabase,
    client,
    librarian,
    test_department,
):
    from app.services.storage_service import MAX_FILE_SIZE_BYTES

    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(
            department_id=test_department
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    oversized_content = (
        b"%PDF-1.7\n"
        + b"x" * MAX_FILE_SIZE_BYTES
    )

    response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "The file must not exceed 50 MB."
    )

    mock_supabase.storage.from_.return_value.upload.assert_not_called()

def test_librarian_can_update_resource_title(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers=headers,
    )
    assert create_response.status_code == 201
    resource_id = create_response.json()["id"]

    response = client.patch(
        f"/resources/{resource_id}",
        json={"title": "Updated Computer Science Book"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Computer Science Book"
    assert data["abstract"] == (
        "A test resource for the university e-library."
    )
    assert data["department_id"] == test_department


def test_student_cannot_update_resource(
    client, librarian, student, test_department
):
    librarian_token = login_and_get_token(
        client, "librarian@test.com"
    )
    create_response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert create_response.status_code == 201
    resource_id = create_response.json()["id"]

    student_token = login_and_get_token(
        client, "student@test.com"
    )
    response = client.patch(
        f"/resources/{resource_id}",
        json={"title": "Unauthorized Change"},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_update_resource(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    create_response = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201

    response = client.patch(
        f"/resources/{create_response.json()['id']}",
        json={"title": "Unauthorized Change"},
    )

    assert response.status_code == 401


def test_update_nonexistent_resource_returns_404(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.patch(
        "/resources/999999",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_update_resource_rejects_duplicate_isbn(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/resources",
        json=resource_payload(
            isbn="9780131103627",
            department_id=test_department,
        ),
        headers=headers,
    )
    second = client.post(
        "/resources",
        json=resource_payload(
            title="Another Book",
            isbn="9780131103628",
            department_id=test_department,
        ),
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/resources/{second.json()['id']}",
        json={"isbn": "9780131103627"},
        headers=headers,
    )

    assert response.status_code == 409


def test_update_resource_rejects_duplicate_doi(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/resources",
        json=resource_payload(
            doi="10.1234/first",
            department_id=test_department,
        ),
        headers=headers,
    )
    second = client.post(
        "/resources",
        json=resource_payload(
            title="Another Research Paper",
            doi="10.1234/second",
            department_id=test_department,
        ),
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/resources/{second.json()['id']}",
        json={"doi": "10.1234/first"},
        headers=headers,
    )

    assert response.status_code == 409


def test_update_resource_rejects_nonexistent_category(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers=headers,
    )
    assert created.status_code == 201

    response = client.patch(
        f"/resources/{created.json()['id']}",
        json={"category_id": 999999},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected category does not exist."
    )


def test_update_resource_rejects_nonexistent_department(
    client, librarian, test_department
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/resources",
        json=resource_payload(department_id=test_department),
        headers=headers,
    )
    assert created.status_code == 201

    response = client.patch(
        f"/resources/{created.json()['id']}",
        json={"department_id": 999999},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The selected department does not exist."
    )

@patch("app.services.storage_service.upload_resource_file")
def test_librarian_can_publish_resource_with_pdf(
    mock_upload,
    client,
    librarian,
    test_department,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resource_response = client.post(
        "/resources",
        json=resource_payload(
            department_id=test_department
        ),
        headers=headers,
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]
    assert resource_response.json()["is_published"] is False

    upload_response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "lecture-notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert upload_response.status_code == 201
    mock_upload.assert_called_once()

    publish_response = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )

    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] is True

def test_librarian_cannot_publish_resource_without_pdf(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    publish_response = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )

    assert publish_response.status_code == 400
    assert publish_response.json()["detail"] == (
        "A resource must have an uploaded PDF before publishing."
    )

def test_student_cannot_publish_resource(
    client,
    librarian,
    student,
):
    librarian_token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers={
            "Authorization": f"Bearer {librarian_token}"
        },
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    student_token = login_and_get_token(
        client, "student@test.com"
    )

    response = client.post(
        f"/resources/{resource_id}/publish",
        headers={
            "Authorization": f"Bearer {student_token}"
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have permission to perform this action."
    )

def test_unauthenticated_user_cannot_publish_resource(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    response = client.post(
        f"/resources/{resource_id}/publish",
    )

    assert response.status_code == 401

def test_librarian_cannot_publish_nonexistent_resource(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    response = client.post(
        "/resources/999999/publish",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found."

@patch("app.services.storage_service.upload_resource_file")
def test_librarian_cannot_publish_already_published_resource(
    mock_upload,
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    upload_response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "lecture-notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert upload_response.status_code == 201

    first_publish = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )

    assert first_publish.status_code == 200
    assert first_publish.json()["is_published"] is True

    second_publish = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )

    assert second_publish.status_code == 400
    assert second_publish.json()["detail"] == (
        "Resource is already published."
    )

    mock_upload.assert_called_once()

@patch("app.services.storage_service.upload_resource_file")
def test_librarian_can_unpublish_resource(
    mock_upload,
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    upload_response = client.post(
        f"/resources/{resource_id}/files",
        files={
            "file": (
                "lecture-notes.pdf",
                b"%PDF-1.7\nTest PDF content",
                "application/pdf",
            )
        },
        headers=headers,
    )

    assert upload_response.status_code == 201

    publish_response = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )

    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] is True

    unpublish_response = client.post(
        f"/resources/{resource_id}/unpublish",
        headers=headers,
    )

    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["is_published"] is False

    mock_upload.assert_called_once()

def test_student_cannot_unpublish_resource(
    client,
    librarian,
    student,
):
    librarian_token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert resource_response.status_code == 201

    resource_id = resource_response.json()["id"]
    student_token = login_and_get_token(
        client, "student@test.com"
    )

    response = client.post(
        f"/resources/{resource_id}/unpublish",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_unpublish_resource(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resource_response.status_code == 201

    resource_id = resource_response.json()["id"]

    response = client.post(
        f"/resources/{resource_id}/unpublish",
    )

    assert response.status_code == 401


def test_unpublish_nonexistent_resource(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )

    response = client.post(
        "/resources/999999/unpublish",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found."


def test_cannot_unpublish_already_unpublished_resource(
    client,
    librarian,
):
    token = login_and_get_token(
        client, "librarian@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    resource_response = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )

    assert resource_response.status_code == 201
    resource_id = resource_response.json()["id"]

    response = client.post(
        f"/resources/{resource_id}/unpublish",
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Resource is already unpublished."
    )

def test_librarian_can_archive_and_unarchive_resource(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )
    assert created.status_code == 201
    resource_id = created.json()["id"]

    archived = client.post(
        f"/resources/{resource_id}/archive",
        headers=headers,
    )

    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert archived.json()["is_published"] is False
    assert archived.json()["archived_at"] is not None

    restored = client.post(
        f"/resources/{resource_id}/unarchive",
        headers=headers,
    )

    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False
    assert restored.json()["is_published"] is False
    assert restored.json()["archived_at"] is None


@pytest.mark.parametrize(
    "action", ["archive", "unarchive"]
)
def test_student_cannot_manage_archiving(
    client, librarian, student, action
):
    librarian_token = login_and_get_token(
        client, "librarian@test.com"
    )

    created = client.post(
        "/resources",
        json=resource_payload(),
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert created.status_code == 201

    student_token = login_and_get_token(
        client, "student@test.com"
    )

    response = client.post(
        f"/resources/{created.json()['id']}/{action}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "action", ["archive", "unarchive"]
)
def test_unauthenticated_user_cannot_manage_archiving(
    client, action
):
    response = client.post(f"/resources/999999/{action}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "action", ["archive", "unarchive"]
)
def test_archive_actions_reject_missing_resource(
    client, librarian, action
):
    token = login_and_get_token(client, "librarian@test.com")

    response = client.post(
        f"/resources/999999/{action}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found."


def test_archive_actions_reject_invalid_transitions(
    client, librarian
):
    token = login_and_get_token(client, "librarian@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/resources",
        json=resource_payload(),
        headers=headers,
    )
    assert created.status_code == 201
    resource_id = created.json()["id"]

    unarchive_first = client.post(
        f"/resources/{resource_id}/unarchive",
        headers=headers,
    )
    assert unarchive_first.status_code == 400

    archived = client.post(
        f"/resources/{resource_id}/archive",
        headers=headers,
    )
    assert archived.status_code == 200

    archive_again = client.post(
        f"/resources/{resource_id}/archive",
        headers=headers,
    )
    assert archive_again.status_code == 400

    publish_archived = client.post(
        f"/resources/{resource_id}/publish",
        headers=headers,
    )
    assert publish_archived.status_code == 400
    assert publish_archived.json()["detail"] == (
        "Archived resources must be restored before publishing."
    )
