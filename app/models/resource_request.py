from datetime import datetime

from sqlalchemy import (
    DateTime,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class ResourceRequest(Base):
    __tablename__ = "resource_requests"
    
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending','under_review','approved', ""'fulfilled', 'rejected', 'cancelled')",
            name="ck_resource_requests_valid_status",
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Request information
    requested_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending", index=True)
    
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    fulfilled_resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    requester: Mapped["User"] = relationship(
        foreign_keys=[requested_by],
    )
    
    reviewer: Mapped["User"] = relationship(
        foreign_keys=[reviewed_by],
    )
    
    fulfilled_resource: Mapped["Resource | None"] = relationship()
    