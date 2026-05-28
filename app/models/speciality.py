import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.symptom import symptom_speciality_map

if TYPE_CHECKING:
    from app.models.doctor import Doctor

# Many-to-many association table mapping doctors to Specialities
doctor_specialities = Table(
    "doctor_specialities",
    Base.metadata,
    Column(
        "doctor_id",
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "speciality_id",
        UUID(as_uuid=True),
        ForeignKey("specialities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Speciality(Base):
    """Speciality Model representing medical disciplines (e.g., Cardiology, Dermatology)."""

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    symptoms: Mapped[List["Symptom"]] = relationship(
        "Symptom",
        secondary=symptom_speciality_map,
        back_populates="specialities",
    )

    # Doctors associated with this speciality
    doctors: Mapped[List["Doctor"]] = relationship(
        "Doctor",
        secondary=doctor_specialities,
        back_populates="specialities",
    )

