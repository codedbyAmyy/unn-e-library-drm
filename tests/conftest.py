import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.database import Base, get_db
from app.models.user import User
from app.models.academic import Faculty, Department
from app.utils.security import hash_password
from app.main import app as fastapi_app
import app.models  # noqa: F401


@pytest.fixture
def test_engine():
    if not settings.TEST_DATABASE_URL:
        pytest.fail(
            "TEST_DATABASE_URL is missing from your .env file."
        )

    engine = create_engine(settings.TEST_DATABASE_URL)

    # Safe only because TEST_DATABASE_URL must point to the
    # dedicated unn_e_library_test database.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture
def test_department(test_engine):
    with Session(test_engine) as db:
        faculty = Faculty(
            name="Test Faculty",
            code="TST",
        )
        db.add(faculty)
        db.flush()

        department = Department(
            name="Computer Science",
            code="TCS",
            faculty_id=faculty.id,
        )
        db.add(department)
        db.commit()
        db.refresh(department)

        department_id = department.id

    return department_id

@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)

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
