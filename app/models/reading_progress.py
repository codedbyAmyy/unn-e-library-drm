"""Actual PDF reading position, unique per student/resource."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("user_id", "resource_id", name="uq_reading_progress_user_resource"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    current_page: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
