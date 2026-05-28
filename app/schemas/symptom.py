from datetime import datetime
import uuid
from pydantic import BaseModel, Field


class SymptomBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Name of the symptom")
    slug: str = Field(..., min_length=2, max_length=120, description="SEO-friendly unique URL slug")
    description: str | None = Field(None, max_length=500, description="Clinical description of the symptom")


class SymptomCreate(SymptomBase):
    pass


class SymptomUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    slug: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=500)


class SymptomResponse(SymptomBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
