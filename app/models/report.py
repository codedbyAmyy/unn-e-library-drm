from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class BrokenResourceReport(Base):
    __tablename__ = "broken_resource_reports"
    
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('open','under_review','resolved', 'dismissed')",
            name="ck_broken_reports_valid_status",
        ),
        CheckConstraint(
            "issue_type IN"
            "('file_unavailable','file_corrupted','incorrect_metadata','access_problem','other')",
            name="ck_broken_reports_valid_issue_type",
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    reported_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Report information
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", server_default="open", index=True)
    
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    reporter: Mapped["User"] = relationship(foreign_keys=[reported_by])
    
    resource: Mapped["Resource"] = relationship()
    
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by])