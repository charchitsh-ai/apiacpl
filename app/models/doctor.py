import uuid
from datetime import datetime, time
from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Time, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.speciality import Speciality


class Doctor(Base):
    """Doctor Profile Model containing professional details, fees, and system availability flags."""

    # Share primary key with Users table (1-to-1 relationship)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(170), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    bio: Mapped[str] = mapped_column(String(1000), nullable=True)
    qualifications: Mapped[str] = mapped_column(String(500), nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    consultation_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False, index=True)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.00, nullable=False, index=True)
    
    # Store list of languages spoken, e.g. ["English", "Hindi"] using Postgres-friendly JSONB type
    languages: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    profile_image: Mapped[str] = mapped_column(String(500), nullable=True)
    city: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    clinic_address: Mapped[str] = mapped_column(String(500), nullable=True)
    
    telemedicine_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    clinic_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    
    specialities: Mapped[List["Speciality"]] = relationship(
        "Speciality",
        secondary="doctor_specialities",
        back_populates="doctors",
    )

    availabilities: Mapped[List["DoctorAvailability"]] = relationship(
        "DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan"
    )

    reviews: Mapped[List["DoctorReview"]] = relationship(
        "DoctorReview", back_populates="doctor", cascade="all, delete-orphan"
    )


class DoctorAvailability(Base):
    """Logs weekly availability slots for a doctor, e.g. Monday 9:00 - 13:00."""

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Monday, 6 = Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="availabilities")


class DoctorReview(Base):
    """Reviews and ratings given by patients to specific doctors."""

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)
    comment: Mapped[str] = mapped_column(String(1000), nullable=True)

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="reviews")
    user: Mapped["User"] = relationship("User")
