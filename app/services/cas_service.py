
"""Current Awareness Service for newly published resources."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Course
from app.models.email_delivery_job import EmailDeliveryJob
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.resource import Resource
from app.models.user import User


def queue_new_resource_notifications(
    db: Session,
    resource: Resource,
) -> int:
    """Create CAS notifications and email jobs without committing."""

    if not resource.is_published or resource.is_archived:
        return 0

    department_id = resource.department_id
    academic_level = None

    if resource.course_id is not None:
        course = db.get(Course, resource.course_id)
        if course is not None:
            if department_id is None:
                department_id = course.department_id
            academic_level = course.academic_level

    users_query = select(User).where(
        User.is_active.is_(True),
        User.role.in_(("student", "lecturer")),
    )

    if department_id is not None:
        users_query = users_query.where(
            User.department_id == department_id
        )

    users = db.scalars(users_query).all()
    created_count = 0

    for user in users:
        # Academic level applies to students only.
        if (
            academic_level is not None
            and user.role == "student"
            and user.academic_level != academic_level
        ):
            continue

        existing = db.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id,
                Notification.resource_id == resource.id,
                Notification.notification_type == "new_resource",
            )
        )

        if existing is not None:
            continue

        preference = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id
            )
        )

        in_app_enabled = (
            preference is None
            or preference.new_resource_in_app
        )
        email_enabled = (
            preference is None
            or preference.new_resource_email
        )

        if not in_app_enabled and not email_enabled:
            continue

        notification = Notification(
            user_id=user.id,
            resource_id=resource.id,
            notification_type="new_resource",
            title="New Academic Resource Available",
            message=(
                f"A new resource, '{resource.title}', "
                "has been published in the UNN E-Library."
            ),
            is_read=False,
        )

        db.add(notification)
        db.flush()

        if email_enabled:
            email_job = EmailDeliveryJob(
                notification_id=notification.id,
                recipient_email=user.email,
                subject="New Resource Available - UNN E-Library",
                body=(
                    f"Hello {user.full_name},\n\n"
                    "A new academic resource relevant to you "
                    "is available in the UNN E-Library.\n\n"
                    f"Title: {resource.title}\n"
                    f"Resource ID: {resource.id}\n\n"
                    "Log in to the E-Library to view it.\n\n"
                    "UNN E-Library"
                ),
                status="pending",
            )
            db.add(email_job)

        created_count += 1

    return created_count
