import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.doctor import Doctor, DoctorAvailability


class Appointment(Base):
    """Appointment Model representing a booking instance between a Patient and a Doctor."""

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    availability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctor_availabilities.id", ondelete="SET NULL"), nullable=True, index=True
    )

    appointment_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consultation_mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # telemedicine, opd, audio
    booking_source: Mapped[str] = mapped_column(String(20), default="web", nullable=False)  # web, app
    symptoms: Mapped[str] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="booked", nullable=False, index=True)  # booked, confirmed, cancelled, completed, no_show, rescheduled
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)

    # Relationships
    patient: Mapped["User"] = relationship("User", foreign_keys=[patient_id])
    doctor: Mapped["Doctor"] = relationship("Doctor")
    availability: Mapped["DoctorAvailability"] = relationship("DoctorAvailability")
    
    status_logs: Mapped[List["AppointmentStatusLog"]] = relationship(
        "AppointmentStatusLog", back_populates="appointment", cascade="all, delete-orphan"
    )


class AppointmentStatusLog(Base):
    """Tracks state transition logs for appointments for auditing purposes."""

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        nullable=False,
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="status_logs")
    modifier: Mapped["User"] = relationship("User", foreign_keys=[changed_by])
