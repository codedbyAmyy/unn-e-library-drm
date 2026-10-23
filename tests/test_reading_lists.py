from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.academic import Course
from app.models.resource import Resource
from app.models.user import User
from app.utils.security import hash_password


def auth(client, email):
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200, response.text
    return {
        "Authorization":
        f"Bearer {response.json()['access_token']}"
    }


def setup_course(test_engine, department_id):
    with Session(test_engine) as db:
        course = Course(
            department_id=department_id,
            course_code="CSC301",
            title="Advanced Database Systems",
            academic_level=300,
            semester="First",
        )
        db.add(course)
        db.commit()
        return course.id


def setup_resource(test_engine, librarian_id):
    with Session(test_engine) as db:
        resource = Resource(
            title="Database Management Systems",
            resource_type="book",
            uploaded_by=librarian_id,
            is_published=True,
            is_archived=False,
            published_at=datetime.now(timezone.utc),
        )
        db.add(resource)
        db.commit()
        return resource.id


def create_lecturer(test_engine, department_id):
    with Session(test_engine) as db:
        lecturer = User(
            full_name="Test Lecturer",
            email="lecturer@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="lecturer",
            department_id=department_id,
        )
        db.add(lecturer)
        db.commit()
        return lecturer.id


def create_list(client, headers, course_id):
    return client.post(
        "/reading-lists",
        json={
            "course_id": course_id,
            "title": "CSC301 Essential Readings",
            "academic_session": "2026/2027",
        },
        headers=headers,
    )


def test_librarian_creates_draft(
    client, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)

    response = create_list(
        client,
        auth(client, "librarian@test.com"),
        course_id,
    )

    assert response.status_code == 201, response.text
    assert response.json()["is_published"] is False
    assert response.json()["created_by"] == librarian
    assert response.json()["items"] == []


def test_student_cannot_create_reading_list(
    client, student, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)

    response = create_list(
        client,
        auth(client, "student@test.com"),
        course_id,
    )

    assert response.status_code == 403


def test_student_cannot_see_draft(
    client, student, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)

    created = create_list(
        client,
        auth(client, "librarian@test.com"),
        course_id,
    )
    assert created.status_code == 201, created.text

    student_auth = auth(client, "student@test.com")
    reading_list_id = created.json()["id"]

    detail = client.get(
        f"/reading-lists/{reading_list_id}",
        headers=student_auth,
    )

    assert detail.status_code == 404

    listing = client.get(
        "/reading-lists",
        headers=student_auth,
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_publish_with_valid_resource(
    client, student, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)

    librarian_auth = auth(client, "librarian@test.com")
    student_auth = auth(client, "student@test.com")

    created = create_list(
        client, librarian_auth, course_id
    )
    assert created.status_code == 201, created.text

    list_id = created.json()["id"]

    added = client.post(
        f"/reading-lists/{list_id}/items",
        json={
            "resource_id": resource_id,
            "notes": "Read chapters 1 through 4.",
            "is_required": True,
        },
        headers=librarian_auth,
    )

    assert added.status_code == 201, added.text
    assert len(added.json()["items"]) == 1
    assert added.json()["items"][0]["position"] == 1

    published = client.post(
        f"/reading-lists/{list_id}/publish",
        headers=librarian_auth,
    )

    assert published.status_code == 200, published.text
    assert published.json()["is_published"] is True

    student_detail = client.get(
        f"/reading-lists/{list_id}",
        headers=student_auth,
    )

    assert student_detail.status_code == 200
    assert student_detail.json()["items"][0]["resource_id"] == resource_id


def test_cannot_publish_empty_list(
    client, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(
        client, librarian_auth, course_id
    )

    response = client.post(
        f"/reading-lists/{created.json()['id']}/publish",
        headers=librarian_auth,
    )

    assert response.status_code == 400


def test_duplicate_resource_rejected(
    client, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(
        client, librarian_auth, course_id
    )
    list_id = created.json()["id"]
    path = f"/reading-lists/{list_id}/items"

    first = client.post(
        path,
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )
    assert first.status_code == 201

    second = client.post(
        path,
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )
    assert second.status_code == 409


def test_lecturer_can_manage_own_list(
    client, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)
    create_lecturer(test_engine, test_department)

    lecturer_auth = auth(client, "lecturer@test.com")

    created = create_list(
        client, lecturer_auth, course_id
    )

    assert created.status_code == 201, created.text

    list_id = created.json()["id"]

    edited = client.patch(
        f"/reading-lists/{list_id}",
        json={"title": "Updated CSC301 Reading List"},
        headers=lecturer_auth,
    )

    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Updated CSC301 Reading List"


def test_published_list_must_be_unpublished_to_edit(
    client, librarian, test_department, test_engine
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(
        client, librarian_auth, course_id
    )
    list_id = created.json()["id"]

    client.post(
        f"/reading-lists/{list_id}/items",
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )

    client.post(
        f"/reading-lists/{list_id}/publish",
        headers=librarian_auth,
    )

    edited = client.patch(
        f"/reading-lists/{list_id}",
        json={"title": "Changed while published"},
        headers=librarian_auth,
    )

    assert edited.status_code == 409

    unpublished = client.post(
        f"/reading-lists/{list_id}/unpublish",
        headers=librarian_auth,
    )

    assert unpublished.status_code == 200
    assert unpublished.json()["is_published"] is False

def test_lecturer_cannot_create_list_for_another_department(
    client, test_engine, test_department
):
    from app.models.academic import Department, Faculty

    create_lecturer(test_engine, test_department)

    with Session(test_engine) as db:
        faculty = Faculty(
            name="Other Faculty",
            code="OTH",
        )
        db.add(faculty)
        db.flush()

        department = Department(
            faculty_id=faculty.id,
            name="Other Department",
            code="OTD",
        )
        db.add(department)
        db.flush()

        course = Course(
            department_id=department.id,
            course_code="OTH301",
            title="Other Department Course",
            academic_level=300,
        )
        db.add(course)
        db.commit()
        other_course_id = course.id

    response = create_list(
        client,
        auth(client, "lecturer@test.com"),
        other_course_id,
    )

    assert response.status_code == 403


def test_lecturer_cannot_edit_another_lecturers_list(
    client, test_engine, test_department
):
    course_id = setup_course(test_engine, test_department)
    create_lecturer(test_engine, test_department)

    with Session(test_engine) as db:
        second_lecturer = User(
            full_name="Second Lecturer",
            email="lecturer2@test.com",
            password_hash=hash_password("TestPassword123!"),
            role="lecturer",
            department_id=test_department,
        )
        db.add(second_lecturer)
        db.commit()

    first_auth = auth(client, "lecturer@test.com")
    second_auth = auth(client, "lecturer2@test.com")

    created = create_list(client, first_auth, course_id)
    assert created.status_code == 201, created.text

    response = client.patch(
        f"/reading-lists/{created.json()['id']}",
        json={"title": "Unauthorized Change"},
        headers=second_auth,
    )

    assert response.status_code == 404


def test_student_cannot_view_list_for_different_level(
    client, student, librarian, test_engine, test_department
):
    with Session(test_engine) as db:
        course = Course(
            department_id=test_department,
            course_code="CSC401",
            title="Advanced Topics",
            academic_level=400,
        )
        db.add(course)
        db.commit()
        course_id = course.id

    resource_id = setup_resource(test_engine, librarian)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(client, librarian_auth, course_id)
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    added = client.post(
        f"/reading-lists/{list_id}/items",
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )
    assert added.status_code == 201, added.text

    published = client.post(
        f"/reading-lists/{list_id}/publish",
        headers=librarian_auth,
    )
    assert published.status_code == 200, published.text

    student_auth = auth(client, "student@test.com")

    detail = client.get(
        f"/reading-lists/{list_id}",
        headers=student_auth,
    )
    assert detail.status_code == 404

    listing = client.get("/reading-lists", headers=student_auth)
    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_librarian_can_remove_draft_reading_item(
    client, librarian, test_engine, test_department
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(client, librarian_auth, course_id)
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    added = client.post(
        f"/reading-lists/{list_id}/items",
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )
    assert added.status_code == 201, added.text

    item_id = added.json()["items"][0]["id"]

    removed = client.delete(
        f"/reading-lists/{list_id}/items/{item_id}",
        headers=librarian_auth,
    )
    assert removed.status_code == 204, removed.text

    detail = client.get(
        f"/reading-lists/{list_id}",
        headers=librarian_auth,
    )
    assert detail.status_code == 200
    assert detail.json()["items"] == []


def test_archived_resource_cannot_be_added(
    client, librarian, test_engine, test_department
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)

    with Session(test_engine) as db:
        resource = db.get(Resource, resource_id)
        resource.is_archived = True
        db.commit()

    librarian_auth = auth(client, "librarian@test.com")
    created = create_list(client, librarian_auth, course_id)
    assert created.status_code == 201, created.text

    response = client.post(
        f"/reading-lists/{created.json()['id']}/items",
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )

    assert response.status_code == 400


def test_cannot_publish_list_if_resource_was_archived(
    client, librarian, test_engine, test_department
):
    course_id = setup_course(test_engine, test_department)
    resource_id = setup_resource(test_engine, librarian)
    librarian_auth = auth(client, "librarian@test.com")

    created = create_list(client, librarian_auth, course_id)
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    added = client.post(
        f"/reading-lists/{list_id}/items",
        json={"resource_id": resource_id},
        headers=librarian_auth,
    )
    assert added.status_code == 201, added.text

    # Archive the resource after adding it to the draft.
    with Session(test_engine) as db:
        resource = db.get(Resource, resource_id)
        resource.is_archived = True
        db.commit()

    published = client.post(
        f"/reading-lists/{list_id}/publish",
        headers=librarian_auth,
    )

    assert published.status_code == 400

    detail = client.get(
        f"/reading-lists/{list_id}",
        headers=librarian_auth,
    )
    assert detail.status_code == 200
    assert detail.json()["is_published"] is False
