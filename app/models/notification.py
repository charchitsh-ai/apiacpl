import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.appointment import Appointment


class Notification(Base):
    """Notification Model representing sent or pending alerts dispatched to users."""

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # appointment_booked, prescription_ready, etc.
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # whatsapp, sms, email, push
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending, sent, failed
    
    # Dynamic values like error traces or SMS statuses
    metadata_json: Mapped[dict] = mapped_column(JSONB, name="metadata", default=dict, nullable=False)
    
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


class NotificationTemplate(Base):
    """Stores body templates with string variables for rendering notification payloads."""

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)  # Subject (only for Email notifications)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    
    # Allowed rendering variables, e.g. ["patient_name", "doctor_name"]
    variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class ReminderJob(Base):
    """Logs scheduled cron/queue background jobs for doctor and patient reminders."""

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 24h_before, 2h_before, followup
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment")
