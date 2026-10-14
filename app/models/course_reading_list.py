from datetime import datetime

from sqlalchemy import (
    Boolean,
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

class CourseReadingList(Base):
    __tablename__ = "course_reading_lists"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Reading list information
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    academic_session: Mapped[str | None] = mapped_column(String(30), nullable=True)
    
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    course: Mapped["Course"] = relationship()
    
    creator: Mapped["User"] = relationship()
    
    items: Mapped[list["CourseReadingListItem"]] = relationship(
        back_populates="reading_list",
        cascade="all, delete-orphan",
        order_by="CourseReadingListItem.position"
    )
    
class CourseReadingListItem(Base):
    __tablename__ = "course_reading_list_items"
    
    __table_args__ = (
        UniqueConstraint(
            "reading_list_id",
            "resource_id",
            name="uq_reading_list_resource",
        ),
        UniqueConstraint(
            "reading_list_id",
            "position",
            name="uq_reading_list_position",
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    reading_list_id: Mapped[int] = mapped_column(
        ForeignKey("course_reading_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Item information
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    reading_list: Mapped["CourseReadingList"] = relationship(back_populates="items")
    
    resource: Mapped["Resource"] = relationship()
    
    