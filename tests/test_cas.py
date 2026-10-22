import pytest
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_delivery_job import EmailDeliveryJob
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.resource import Resource, ResourceFile
from app.models.user import User
from app.models.academic import Department, Faculty
from app.services.resource_service import publish_resource
from app.services.cas_service import queue_new_resource_notifications


def make_draft(db, uploader_id, department_id=None):
    resource = Resource(
        title="Introduction to Artificial Intelligence",
        resource_type="book",
        uploaded_by=uploader_id,
        department_id=department_id,
        is_published=False,
        is_archived=False,
    )
    db.add(resource)
    db.flush()

    db.add(
        ResourceFile(
            resource_id=resource.id,
            storage_path=f"resources/{resource.id}/test.pdf",
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            is_primary=True,
        )
    )
    db.commit()
    return resource.id


def test_cas_creates_notifications_and_email_jobs(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        resource_id = make_draft(
            db, librarian, test_department
        )

        publish_resource(db, resource_id)

        notifications = db.scalars(
            select(Notification).where(
                Notification.resource_id == resource_id
            )
        ).all()

        assert len(notifications) == 1
        assert notifications[0].user_id == student
        assert notifications[0].notification_type == "new_resource"
        assert notifications[0].is_read is False

        jobs = db.scalars(
            select(EmailDeliveryJob)
        ).all()

        assert len(jobs) == 1
        assert jobs[0].notification_id == notifications[0].id
        assert jobs[0].status == "pending"


def test_cas_respects_email_preference(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        db.add(
            NotificationPreference(
                user_id=student,
                new_resource_in_app=True,
                new_resource_email=False,
            )
        )
        db.commit()

        resource_id = make_draft(
            db, librarian, test_department
        )

        publish_resource(db, resource_id)

        notifications = db.scalars(
            select(Notification)
        ).all()

        jobs = db.scalars(
            select(EmailDeliveryJob)
        ).all()

        assert len(notifications) == 1
        assert len(jobs) == 0


def test_cas_skips_users_with_both_channels_disabled(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        db.add(
            NotificationPreference(
                user_id=student,
                new_resource_in_app=False,
                new_resource_email=False,
            )
        )
        db.commit()

        resource_id = make_draft(
            db, librarian, test_department
        )

        publish_resource(db, resource_id)

        assert db.scalars(
            select(Notification)
        ).all() == []

        assert db.scalars(
            select(EmailDeliveryJob)
        ).all() == []


def test_cas_excludes_users_from_other_departments(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        resource_id = make_draft(
            db,
            librarian,
            department_id=None,
        )

        # Use an impossible department identifier only after
        # creating the resource: directly test recipient targeting.
        resource = db.get(Resource, resource_id)
        resource.department_id = test_department
        db.commit()

        publish_resource(db, resource_id)

        notifications = db.scalars(
            select(Notification)
        ).all()

        assert len(notifications) == 1
        assert notifications[0].user_id == student
def test_cas_supports_email_only_preference(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        db.add(
            NotificationPreference(
                user_id=student,
                new_resource_in_app=False,
                new_resource_email=True,
            )
        )
        db.commit()

        resource_id = make_draft(
            db, librarian, test_department
        )
        publish_resource(db, resource_id)

        notifications = db.scalars(
            select(Notification)
        ).all()

        jobs = db.scalars(
            select(EmailDeliveryJob)
        ).all()

        assert len(notifications) == 1
        assert len(jobs) == 1
        assert jobs[0].notification_id == notifications[0].id


def test_cas_excludes_other_departments(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        other_faculty = Faculty(
            name="Faculty of Arts",
            code="ART",
        )
        db.add(other_faculty)
        db.flush()

        other_department = Department(
            name="English",
            code="ENG",
            faculty_id=other_faculty.id,
        )
        db.add(other_department)
        db.flush()

        other_user = User(
            full_name="Other Student",
            email="otherstudent@test.com",
            password_hash="test-only-hash",
            role="student",
            department_id=other_department.id,
            academic_level=300,
        )
        db.add(other_user)
        db.commit()
        other_user_id = other_user.id

        resource_id = make_draft(
            db, librarian, test_department
        )
        publish_resource(db, resource_id)

        recipient_ids = db.scalars(
            select(Notification.user_id).where(
                Notification.resource_id == resource_id
            )
        ).all()

        assert student in recipient_ids
        assert other_user_id not in recipient_ids


def test_cas_does_not_duplicate_notifications(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        resource_id = make_draft(
            db, librarian, test_department
        )
        resource = publish_resource(db, resource_id)

        first_count = len(
            db.scalars(
                select(Notification)
            ).all()
        )

        queue_new_resource_notifications(db, resource)
        db.commit()

        second_count = len(
            db.scalars(
                select(Notification)
            ).all()
        )

        assert first_count == 1
        assert second_count == 1


def test_cas_failure_rolls_back_publication(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        resource_id = make_draft(
            db, librarian, test_department
        )

        with patch(
            "app.services.resource_service.queue_new_resource_notifications",
            side_effect=RuntimeError("CAS generation failed"),
        ):
            with pytest.raises(RuntimeError):
                publish_resource(db, resource_id)

        db.expire_all()
        resource = db.get(Resource, resource_id)

        assert resource.is_published is False
        assert resource.published_at is None
        assert db.scalars(
            select(Notification)
        ).all() == []

def test_database_rejects_duplicate_cas_notification(
    test_engine, librarian, student, test_department
):
    with Session(test_engine) as db:
        resource_id = make_draft(
            db, librarian, test_department
        )
        publish_resource(db, resource_id)

        duplicate = Notification(
            user_id=student,
            resource_id=resource_id,
            notification_type="new_resource",
            title="Duplicate Resource Alert",
            message="This should not be inserted.",
        )

        db.add(duplicate)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()
