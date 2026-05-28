from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, EmailStr, Field
from app.schemas.speciality import SpecialityResponse


class DoctorProfileBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    slug: str = Field(..., min_length=2, max_length=170, description="SEO-friendly slug")
    email: EmailStr
    bio: str | None = Field(None, max_length=1000)
    qualifications: str | None = Field(None, max_length=500)
    experience_years: int = Field(0, ge=0)
    consultation_fee: float = Field(0.0, ge=0.0)
    languages: List[str] = Field(default_factory=list, description="Spoken languages list")
    profile_image: str | None = Field(None, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    clinic_address: str | None = Field(None, max_length=500)
    telemedicine_enabled: bool = True
    clinic_enabled: bool = True
    is_available: bool = True


class DoctorProfileCreate(DoctorProfileBase):
    id: uuid.UUID = Field(..., description="The user account ID linked to this doctor profile")


class DoctorProfileUpdate(BaseModel):
    full_name: str | None = None
    slug: str | None = None
    email: EmailStr | None = None
    bio: str | None = None
    qualifications: str | None = None
    experience_years: int | None = None
    consultation_fee: float | None = None
    languages: List[str] | None = None
    profile_image: str | None = None
    city: str | None = None
    clinic_address: str | None = None
    telemedicine_enabled: bool | None = None
    clinic_enabled: bool | None = None
    verification_status: str | None = None
    is_available: bool | None = None


class DoctorProfileResponse(DoctorProfileBase):
    id: uuid.UUID
    rating: float
    verification_status: str
    created_at: datetime
    updated_at: datetime
    specialities: List[SpecialityResponse] = []

    class Config:
        from_attributes = True


class DoctorPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[DoctorProfileResponse]
