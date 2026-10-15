import pytest
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
