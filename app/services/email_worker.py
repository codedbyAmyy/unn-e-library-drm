
"""Process queued CAS email notifications."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.email_delivery_job import EmailDeliveryJob
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.services.email_service import send_notification_email


MAX_ATTEMPTS = 3
LEASE_SECONDS = 120


def utc_now():
    return datetime.now(timezone.utc)


def process_next_email_job(db: Session) -> bool:
    """Claim and process one due job.

    Returns False when no work is available.
    """

    now = utc_now()

    job = db.scalar(
        select(EmailDeliveryJob)
        .where(
            EmailDeliveryJob.attempt_count < MAX_ATTEMPTS,
            or_(
                EmailDeliveryJob.status.in_(
                    ("pending", "failed")
                ),
                EmailDeliveryJob.status == "processing",
            ),
            or_(
                EmailDeliveryJob.next_attempt_at.is_(None),
                EmailDeliveryJob.next_attempt_at <= now,
            ),
        )
        .order_by(
            EmailDeliveryJob.created_at,
            EmailDeliveryJob.id,
        )
        .with_for_update(skip_locked=True)
        .limit(1)
    )

    if job is None:
        return False

    job.status = "processing"
    job.attempt_count += 1
    job.next_attempt_at = now + timedelta(
        seconds=LEASE_SECONDS
    )

    job_id = job.id

    # Release the row lock before contacting SMTP.
    db.commit()

    job = db.get(EmailDeliveryJob, job_id)

    recipient = db.scalar(
        select(User)
        .join(
            Notification,
            Notification.user_id == User.id,
        )
        .where(
            Notification.id == job.notification_id
        )
    )

    if recipient is None or not recipient.is_active:
        job.status = "failed"
        job.attempt_count = MAX_ATTEMPTS
        job.last_error = "Recipient is unavailable."
        job.next_attempt_at = None
        db.commit()
        return True

    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == recipient.id
        )
    )

    if (
        preference is not None
        and not preference.new_resource_email
    ):
        # Reuse the terminal failed state to mark a
        # deliberately suppressed email.
        job.status = "failed"
        job.attempt_count = MAX_ATTEMPTS
        job.last_error = "Recipient disabled email alerts."
        job.next_attempt_at = None
        db.commit()
        return True

    try:
        send_notification_email(
            recipient=job.recipient_email,
            subject=job.subject,
            body=job.body,
        )
    except Exception:
        job.status = "failed"
        # Avoid storing exception text: it could contain
        # server details or credentials.
        job.last_error = "Email delivery attempt failed."

        if job.attempt_count < MAX_ATTEMPTS:
            job.next_attempt_at = utc_now() + timedelta(
                minutes=2 ** job.attempt_count
            )
        else:
            job.next_attempt_at = None

        db.commit()
        return True

    job.status = "sent"
    job.sent_at = utc_now()
    job.next_attempt_at = None
    job.last_error = None
    db.commit()

    return True


def process_email_queue(
    db: Session,
    batch_size: int = 20,
) -> int:
    processed = 0

    for _ in range(batch_size):
        if not process_next_email_job(db):
            break
        processed += 1

    return processed
