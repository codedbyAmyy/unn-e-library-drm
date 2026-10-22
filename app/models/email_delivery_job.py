
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailDeliveryJob(Base):
    __tablename__ = "email_delivery_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')",
            name="ck_email_delivery_jobs_valid_status",
        ),
        UniqueConstraint(
            "notification_id",
            name="uq_email_delivery_jobs_notification",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    notification_id: Mapped[int] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    notification: Mapped["Notification"] = relationship()
