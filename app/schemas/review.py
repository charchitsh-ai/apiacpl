from datetime import datetime
import uuid
from pydantic import BaseModel, Field


class ReviewBase(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    comment: str | None = Field(None, max_length=1000, description="Optional review comment")


class ReviewCreate(ReviewBase):
    pass


class ReviewResponse(ReviewBase):
    id: uuid.UUID
    doctor_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
