from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "resource_id",
            name="uq_bookmarks_user_resource",
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship()
    
    resource: Mapped["Resource"] = relationship()
    
class ReadingHistory(Base):
    __tablename__ = "reading_history"
    
    __table_args__ = (
        CheckConstraint(
          "duration_seconds >= 0",
          name="ck_reading_history_duration_non_negative"  
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Reading information
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    
    # Relationships
    user: Mapped["User"] = relationship()
    
    resource: Mapped["Resource"] = relationship()