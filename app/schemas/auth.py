from datetime import datetime
import re
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    # Support login via either email or phone
    username: str = Field(..., description="Email address or phone number")
    password: str = Field(..., description="Plaintext password")
    device_name: str | None = Field(None, description="Client device description")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class SendOtpRequest(BaseModel):
    phone: str = Field(..., description="Mobile number to receive OTP")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91[\-\s]?)?[6-9]\d{9}$", clean_number):
            raise ValueError("Invalid Indian mobile number format.")
        return clean_number


class VerifyOtpRequest(BaseModel):
    phone: str = Field(..., description="Mobile number")
    otp_code: str = Field(..., min_length=4, max_length=6, description="OTP code received")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91[\-\s]?)?[6-9]\d{9}$", clean_number):
            raise ValueError("Invalid Indian mobile number format.")
        return clean_number


class ForgotPasswordRequest(BaseModel):
    phone: str = Field(..., description="Mobile number associated with the account")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91[\-\s]?)?[6-9]\d{9}$", clean_number):
            raise ValueError("Invalid Indian mobile number format.")
        return clean_number


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., description="Mobile number associated with the account")
    otp_code: str = Field(..., description="Verified OTP code")
    new_password: str = Field(..., min_length=8, description="Strong new password")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_number = re.sub(r"\s+", "", v)
        if not re.match(r"^(\+91[\-\s]?)?[6-9]\d{9}$", clean_number):
            raise ValueError("Invalid Indian mobile number format.")
        return clean_number

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Stored secure Refresh Token")


class DeviceSessionResponse(BaseModel):
    id: uuid.UUID
    device_name: str | None
    ip_address: str | None
    user_agent: str | None
    last_active_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
