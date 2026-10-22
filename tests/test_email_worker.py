from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_delivery_job import EmailDeliveryJob
from app.models.notification_preference import NotificationPreference
from app.services.email_worker import (
    process_email_queue,
)
from app.services.resource_service import publish_resource
from tests.test_cas import make_draft


def create_pending_job(db, librarian, department_id):
    resource_id = make_draft(
        db,
        librarian,
        department_id,
    )
    publish_resource(db, resource_id)

    return db.scalar(
        select(EmailDeliveryJob.id)
    )


@patch("app.services.email_worker.send_notification_email")
def test_worker_sends_pending_email(
    mock_send,
    test_engine,
    librarian,
    student,
    test_department,
):
    with Session(test_engine) as db:
        job_id = create_pending_job(
            db, librarian, test_department
        )

        assert process_email_queue(db) == 1

        job = db.get(EmailDeliveryJob, job_id)
        assert job.status == "sent"
        assert job.attempt_count == 1
        assert job.sent_at is not None

        assert process_email_queue(db) == 0
        mock_send.assert_called_once()


@patch("app.services.email_worker.send_notification_email")
def test_worker_retries_failed_email(
    mock_send,
    test_engine,
    librarian,
    student,
    test_department,
):
    mock_send.side_effect = RuntimeError("SMTP unavailable")

    with Session(test_engine) as db:
        job_id = create_pending_job(
            db, librarian, test_department
        )

        assert process_email_queue(db) == 1

        job = db.get(EmailDeliveryJob, job_id)
        assert job.status == "failed"
        assert job.attempt_count == 1
        assert job.next_attempt_at is not None

        # Not immediately eligible for another attempt.
        assert process_email_queue(db) == 0


@patch("app.services.email_worker.send_notification_email")
def test_worker_respects_updated_email_preference(
    mock_send,
    test_engine,
    librarian,
    student,
    test_department,
):
    with Session(test_engine) as db:
        job_id = create_pending_job(
            db, librarian, test_department
        )

        db.add(
            NotificationPreference(
                user_id=student,
                new_resource_in_app=True,
                new_resource_email=False,
            )
        )
        db.commit()

        assert process_email_queue(db) == 1

        job = db.get(EmailDeliveryJob, job_id)
        assert job.status == "failed"
        assert job.last_error == "Recipient disabled email alerts."

        mock_send.assert_not_called()

@patch("app.services.email_worker.send_notification_email")
def test_worker_recovers_expired_processing_job(
    mock_send,
    test_engine,
    librarian,
    student,
    test_department,
):
    with Session(test_engine) as db:
        job_id = create_pending_job(
            db, librarian, test_department
        )

        job = db.get(EmailDeliveryJob, job_id)
        job.status = "processing"
        job.attempt_count = 1
        job.next_attempt_at = (
            datetime.now(timezone.utc)
            - timedelta(minutes=5)
        )
        db.commit()

        assert process_email_queue(db) == 1

        db.refresh(job)

        assert job.status == "sent"
        assert job.attempt_count == 2
        assert job.sent_at is not None

        mock_send.assert_called_once()
