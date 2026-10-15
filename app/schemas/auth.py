from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: Literal["student", "lecturer"]

    matric_number: str | None = Field(default=None, max_length=30)
    staff_id: str | None = Field(default=None, max_length=30)
    department_id: int | None = Field(default=None, gt=0)
    academic_level: int | None = Field(default=None)

    @field_validator("matric_number")
    @classmethod
    def validate_matric_number(cls, value: str | None) -> str | None:
        if value is not None:
            import re

            if not re.fullmatch(r"\d{4}/\d{6}", value):
                raise ValueError(
                    "Matric number must follow the format YYYY/NNNNNN, "
                    "for example 2022/250100."
                )
        return value

    @field_validator("academic_level")
    @classmethod
    def validate_academic_level(cls, value: int | None) -> int | None:
        if value is not None and value not in {100, 200, 300, 400, 500, 600}:
            raise ValueError(
                "Academic level must be 100, 200, 300, 400, 500, or 600."
            )
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: Literal["student", "lecturer", "librarian", "admin"]
    is_active: bool
    must_change_password: bool
    matric_number: str | None
    staff_id: str | None
    department_id: int | None
    academic_level: int | None
    created_at: datetime

class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(min_length=2, max_length=100)