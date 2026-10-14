from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'lecturer', 'librarian', 'admin')",
            name="ck_users_valid_role"
        ),
    )
    
    #Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Basic account information
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Authorization
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student", server_default="student")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    
    # Academic information
    matric_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    
    staff_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    academic_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Account activity
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    department: Mapped["Department | None"] = relationship(back_populates="users")