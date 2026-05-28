import re
from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Unique email address of the user")
    phone: str = Field(..., description="Mobile number with country code, e.g., +919876543210")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, v: str) -> str:
        # Simple Indian mobile number validation format: optionally +91 followed by 10 digits
        clean_number = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91[\-\s]?)?[6-9]\d{9}$", clean_number):
            raise ValueError(
                "Invalid mobile number format. Please supply a valid Indian mobile number."
            )
        return clean_number


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Strong user password")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    phone: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
