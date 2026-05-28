from datetime import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class AppointmentStatusLogResponse(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    old_status: str
    new_status: str
    changed_by: Optional[uuid.UUID]
    changed_at: datetime

    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    doctor_id: uuid.UUID = Field(..., description="Doctor ID for the consultation")
    availability_id: Optional[uuid.UUID] = Field(None, description="Doctor Availability schedule ID")
    appointment_datetime: datetime = Field(..., description="Date and time of appointment (timezone aware)")
    consultation_mode: str = Field(..., description="Mode: telemedicine, opd, audio")
    booking_source: str = Field("web", description="Source: web, app")
    symptoms: Optional[str] = Field(None, max_length=1000, description="Patient symptoms description")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional patient notes")

    @field_validator("consultation_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        modes = ["telemedicine", "opd", "audio"]
        if v.lower() not in modes:
            raise ValueError(f"Consultation mode must be one of {modes}")
        return v.lower()


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        statuses = ["booked", "confirmed", "cancelled", "completed", "no_show", "rescheduled"]
        if v.lower() not in statuses:
            raise ValueError(f"Appointment status must be one of {statuses}")
        return v.lower()


class AppointmentReschedule(BaseModel):
    availability_id: Optional[uuid.UUID] = Field(None, description="New doctor availability schedule ID")
    appointment_datetime: datetime = Field(..., description="New date and time of appointment")


class AppointmentResponse(AppointmentBase):
    id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    status_logs: List[AppointmentStatusLogResponse] = []

    class Config:
        from_attributes = True


class AppointmentPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AppointmentResponse]
