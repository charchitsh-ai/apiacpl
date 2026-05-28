import uuid
from typing import List
from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

# Many-to-many association table between Symptoms and Specialities
symptom_speciality_map = Table(
    "symptom_speciality_map",
    Base.metadata,
    Column(
        "symptom_id",
        UUID(as_uuid=True),
        ForeignKey("symptoms.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "speciality_id",
        UUID(as_uuid=True),
        ForeignKey("specialities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Symptom(Base):
    """Symptom Model representing clinical symptoms used for doctor discovery routing."""

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    specialities: Mapped[List["Speciality"]] = relationship(
        "Speciality",
        secondary=symptom_speciality_map,
        back_populates="symptoms",
    )
