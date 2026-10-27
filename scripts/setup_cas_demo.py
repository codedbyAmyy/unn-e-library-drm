
"""Create controlled CAS demonstration accounts.

Run only against the local development database.
Does not publish resources or send emails.
"""

from getpass import getpass

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.academic import Department, Faculty
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user
from app.utils.security import hash_password


def main():
    print("UNN E-Library: CAS demonstration setup")
    print("Use ONLY your local development database.")
    print("This script does not send emails.")

    confirmation = input(
        "Type SETUP CAS DEMO to continue: "
    ).strip()

    if confirmation != "SETUP CAS DEMO":
        print("Cancelled.")
        return

    student_email = input(
        "Enter your designated test Gmail address: "
    ).strip().lower()

    if not student_email or "@" not in student_email:
        print("A valid test email is required.")
        return

    student_password = getpass(
        "Create a student demo password (12+ characters): "
    )
    librarian_password = getpass(
        "Create a librarian demo password (12+ characters): "
    )

    if (
        len(student_password) < 12
        or len(librarian_password) < 12
    ):
        print("Both passwords must have at least 12 characters.")
        return

    with SessionLocal() as db:
        existing_users = db.scalar(
            select(func.count(User.id))
        ) or 0

        if existing_users != 0:
            print(
                "Cancelled: database already contains users. "
                "No changes were made."
            )
            return

        try:
            faculty = Faculty(
                name="Faculty of Physical Sciences",
                code="FPS",
            )
            db.add(faculty)
            db.flush()

            department = Department(
                name="Computer Science",
                code="CSC",
                faculty_id=faculty.id,
            )
            db.add(department)
            db.commit()

            department_id = department.id

            student_data = RegisterRequest(
                full_name="CAS Demo Student",
                email=student_email,
                password=student_password,
                role="student",
                matric_number="2026/250100",
                department_id=department_id,
                academic_level=300,
            )

            student = register_user(db, student_data)
            student_id = student.id

            librarian = User(
                full_name="CAS Demo Librarian",
                email="cas-librarian@example.test",
                password_hash=hash_password(
                    librarian_password
                ),
                role="librarian",
                is_active=True,
                department_id=department_id,
            )
            db.add(librarian)
            db.commit()

            print("\nCAS demo accounts created.")
            print("Faculty: Faculty of Physical Sciences")
            print("Department: Computer Science")
            print(f"Department ID: {department_id}")
            print(f"Student ID: {student_id}")
            print(f"Librarian ID: {librarian.id}")
            print("Student email: configured test inbox")
            print("Librarian email: cas-librarian@example.test")
            print("\nNo emails were sent.")

        except Exception:
            db.rollback()
            print(
                "Setup encountered an error. "
                "Inspect development records before retrying."
            )
            raise


if __name__ == "__main__":
    main()
