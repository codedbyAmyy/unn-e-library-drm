from typing import Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ResourceType = Literal[
    "book",
    "journal",
    "article",
    "thesis",
    "dissertation",
    "lecture_note",
    "conference_paper",
    "research_paper",
    "report",
    "other",
]

class ResourceCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    abstract: str | None = Field(default=None, max_length=1000)
    resource_type: ResourceType
    publication_year: int | None = Field(default=None, ge=1000, le=9999)
    publisher: str | None = Field(default=None, max_length=200)
    isbn: str | None = Field(default=None, max_length=20)
    doi: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default="English",min_length=1,max_length=50)
    category_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)
    course_id: int | None = Field(default=None, gt=0)
    
    @field_validator(
        "title",
        "language",
        "publisher",
        "isbn",
        "doi",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value
    
    @field_validator("title", "language")
    @classmethod
    def reject_blank_required_text(cls, value, str) -> str:
        if not value:
            raise ValueError("This field cannot be blank.") 
        return value

class ResourceUpdateRequest(BaseModel):
    """Validate partial updates to an existing library resource."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    abstract: str | None = Field(default=None, max_length=1000)
    resource_type: ResourceType | None = None
    publication_year: int | None = Field(default=None, ge=1000, le=9999)
    publisher: str | None = Field(default=None, max_length=200)
    isbn: str | None = Field(default=None, max_length=20)
    doi: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, min_length=1, max_length=50)
    category_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)
    course_id: int | None = Field(default=None, gt=0)

    @field_validator(
        "title",
        "language",
        "publisher",
        "isbn",
        "doi",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("title", "language")
    @classmethod
    def reject_blank_required_text(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("This field cannot be blank.")
        return value

class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    abstract: str | None
    resource_type: str
    publication_year: int | None
    publisher: str | None
    isbn: str | None
    doi: str | None
    language: str
    category_id: int | None
    department_id: int | None
    course_id: int | None
    uploaded_by: int
    is_published: bool
    is_featured: bool
    is_archived: bool
    archived_at: datetime | None