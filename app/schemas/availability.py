from datetime import time
import uuid
from pydantic import BaseModel, Field, field_validator


class AvailabilityBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0 = Monday, 6 = Sunday")
    start_time: time = Field(..., description="Daily start time of consultation")
    end_time: time = Field(..., description="Daily end time of consultation")
    is_available: bool = Field(True, description="Availability flag")

    @field_validator("end_time")
    @classmethod
    def validate_times(cls, end: time, info) -> time:
        if "start_time" in info.data and end <= info.data["start_time"]:
            raise ValueError("End time must be strictly after the start time.")
        return end


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityResponse(AvailabilityBase):
    id: uuid.UUID
    doctor_id: uuid.UUID

    class Config:
        from_attributes = True
