
from datetime import datetime

from sqlalchemy import (
    Boolean,
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

class Category(Base):
    __tablename__ = "categories"
        
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
        
    # Category information
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
        
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
        
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
        
    resources: Mapped[list["Resource"]] = relationship("Resource", back_populates="category",)
        
class Resource(Base):
    __tablename__ = "resources"
    
    __table_args__ = (
        CheckConstraint(
            "resource_type IN "
            "('book', 'journal', 'article', 'thesis', "
            "'dissertation', 'lecture_note', 'conference_paper', "
            "'research_paper', 'report', 'other')",
            name="ck_resources_valid_type",
        ),
        CheckConstraint(
            "publication_year IS NULL OR"
            " publication_year >= 1000 AND publication_year <= 9999",
            name="ck_resources_valid_publication_year",
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Resource information
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    publisher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    
    doi: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="English", server_default="English")
    
    # Foreign keys
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    course_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Resource activity
    uploaded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    category: Mapped["Category | None"] = relationship(back_populates="resources")
    
    files: Mapped[list["ResourceFile"]] = relationship(back_populates="resource", cascade="all, delete-orphan")
    
    authors: Mapped[list["ResourceAuthor"]] = relationship(back_populates="resource", cascade="all, delete-orphan")
    
class ResourceFile(Base):
    __tablename__ = "resource_files"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to Resource
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="true")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    resource: Mapped["Resource"] = relationship(back_populates="files")
        
class ResourceAuthor(Base):
    __tablename__ = "resource_authors"
    
    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "author_name",
            name="uq_resource_authors_resource_name",
        ),
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )
    
    #Foreign key to Resource
    resource_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Author information
    author_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    
    author_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1"
    )
    
    # Relationships
    resource: Mapped["Resource"] = relationship(
        back_populates="authors"
    )
