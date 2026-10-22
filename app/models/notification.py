from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    __table_args__ = (
        CheckConstraint(
            "notification_type IN "
            "('general', 'new_resource','resource_request','course_reading_list', 'system')",
            name="ck_notifications_valid_type",
        ),
        Index(
            "uq_notifications_new_resource_user_resource",
            "user_id",
            "resource_id",
            unique=True,
            postgresql_where=text(
                "notification_type = 'new_resource' "
                "AND resource_id IS NOT NULL"
            ),
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to User
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Notification information
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, default="general", server_default="general", index=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    
    in_app_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    # Foreign key to related resource
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Timestamps
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    # Relationships
    user: Mapped["User"] = relationship()
    
    resource: Mapped["Resource | None"] = relationship()
    
    