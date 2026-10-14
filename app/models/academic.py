from datetime import datetime

from sqlalchemy import (
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


class Faculty(Base):
    __tablename__ = "faculties"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Faculty information
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    departments: Mapped[list["Department"]] = relationship("Department", back_populates="faculty", cascade="all, delete-orphan")
    
class Department(Base):
    __tablename__ = "departments"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to Faculty
    faculty_id: Mapped[int] = mapped_column(Integer, ForeignKey("faculties.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Department information
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    faculty: Mapped["Faculty"] = relationship("Faculty", back_populates="departments")
    
    courses: Mapped[list["Course"]] = relationship("Course", back_populates="department", cascade="all, delete-orphan")
    
    users: Mapped[list["User"]] = relationship(back_populates="department")
    
    __table_args__ = (
        UniqueConstraint(
            "faculty_id", 
            "name", name="uq_departments_faculty_id_name"
        ),
    )
    
class Course(Base):
    __tablename__ = "courses"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign key to Department
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Course information
    course_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    academic_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    semester: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    department: Mapped["Department"] = relationship("Department", back_populates="courses")
    
    __table_args__ = (
        UniqueConstraint(
            "department_id", 
            "course_code", name="uq_courses_department_id_course_code"
        ),
    )