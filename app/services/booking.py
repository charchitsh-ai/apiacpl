from datetime import datetime, timezone
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import (
    AppException,
    NotFoundException,
    PermissionException,
    ValidationException,
)
from app.models.appointment import Appointment
from app.models.doctor import Doctor, DoctorAvailability
from app.repositories.appointment import AppointmentRepository
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule


class BookingService:
    """Service layer managing transaction-safe clinical scheduling, schedules audits, and ownership checks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.appointment_repo = AppointmentRepository(db)

    async def create_appointment(self, patient_id: uuid.UUID, create_in: AppointmentCreate) -> Appointment:
        """
        Creates an appointment with multi-layer transaction safety:
        1. Validates doctor availability profile.
        2. Validates availability schedule day and consultation hours.
        3. Prevents overlapping double bookings.
        4. Logs auditing history.
        """
        # Ensure UTC timezone aware
        appt_time = create_in.appointment_datetime
        if appt_time.tzinfo is None:
            appt_time = appt_time.replace(tzinfo=timezone.utc)

        # 1. Validate Doctor profile
        doctor_stmt = select(Doctor).filter(Doctor.id == create_in.doctor_id)
        doctor_res = await self.db.execute(doctor_stmt)
        doctor = doctor_res.scalars().first()
        if not doctor:
            raise NotFoundException(message="Doctor profile does not exist.")
        if not doctor.is_available or doctor.verification_status != "verified":
            raise ValidationException(message="Doctor is currently not accepting bookings.")

        # 2. Validate Availability Schedule
        if create_in.availability_id:
            avail_stmt = select(DoctorAvailability).filter(
                and_(
                    DoctorAvailability.id == create_in.availability_id,
                    DoctorAvailability.doctor_id == create_in.doctor_id,
                )
            ) if "and_" in globals() else select(DoctorAvailability).filter(
                DoctorAvailability.id == create_in.availability_id
            ).filter(DoctorAvailability.doctor_id == create_in.doctor_id)
            
            avail_res = await self.db.execute(avail_stmt)
            availability = avail_res.scalars().first()
            if not availability or not availability.is_available:
                raise ValidationException(message="Selected availability slot is invalid or inactive.")

            # Validate weekday (Python weekday: 0=Monday, 6=Sunday)
            if appt_time.weekday() != availability.day_of_week:
                raise ValidationException(
                    message=f"Appointment date weekday ({appt_time.strftime('%A')}) does not match scheduling slot."
                )

            # Validate start/end hour boundaries
            appt_time_only = appt_time.time()
            if not (availability.start_time <= appt_time_only <= availability.end_time):
                raise ValidationException(
                    message=f"Appointment time {appt_time_only} is outside available hours ({availability.start_time} - {availability.end_time})."
                )

        # 3. Prevent Double Booking
        is_double_booked = await self.appointment_repo.check_double_booking(
            doctor_id=create_in.doctor_id, appointment_datetime=appt_time
        )
        if is_double_booked:
            raise ValidationException(
                message="This doctor already has an active appointment booked within this time window."
            )

        # 4. Save and audit in a single rollback-safe database transaction block
        try:
            # Create appointment
            appt_data = create_in.model_dump()
            appt_data["patient_id"] = patient_id
            appt_data["appointment_datetime"] = appt_time
            appt_data["status"] = "booked"

            appointment = await self.appointment_repo.create(appt_data)

            # Log transition None -> booked
            await self.appointment_repo.add_status_log(
                appointment_id=appointment.id,
                old_status="None",
                new_status="booked",
                changed_by=patient_id,
            )
            await self.db.commit()
            
            # Refresh to load relationships (e.g. status_logs)
            return await self.appointment_repo.get_with_logs(appointment.id)

        except Exception as e:
            await self.db.rollback()
            raise AppException(
                code="BOOKING_FAILED",
                message=f"Failed to record appointment: {str(e)}",
                status_code=500,
            )

    async def get_appointment(self, appointment_id: uuid.UUID, user_id: uuid.UUID) -> Appointment:
        """Retrieves appointment details after performing strict ownership checks."""
        appointment = await self.appointment_repo.get_with_logs(appointment_id)
        if not appointment:
            raise NotFoundException(message="Appointment not found.")

        # Ensure user is either patient or doctor associated
        if appointment.patient_id != user_id and appointment.doctor_id != user_id:
            raise PermissionException(message="You do not have access rights to view this appointment.")

        return appointment

    async def cancel_appointment(self, appointment_id: uuid.UUID, user_id: uuid.UUID) -> Appointment:
        """Cancels an appointment, logs status changes, and manages transaction safety."""
        appointment = await self.appointment_repo.get_with_logs(appointment_id)
        if not appointment:
            raise NotFoundException(message="Appointment not found.")

        # Ownership audit
        if appointment.patient_id != user_id and appointment.doctor_id != user_id:
            raise PermissionException(message="You are not authorized to cancel this appointment.")

        # State validation
        if appointment.status in ["cancelled", "completed", "no_show"]:
            raise ValidationException(
                message=f"Appointment cannot be cancelled as it is already marked '{appointment.status}'."
            )

        old_status = appointment.status
        try:
            appointment.status = "cancelled"
            await self.appointment_repo.add_status_log(
                appointment_id=appointment.id,
                old_status=old_status,
                new_status="cancelled",
                changed_by=user_id,
            )
            await self.db.commit()
            return appointment
        except Exception as e:
            await self.db.rollback()
            raise AppException(
                code="CANCELLATION_FAILED",
                message=f"Failed to cancel appointment: {str(e)}",
                status_code=500,
            )

    async def reschedule_appointment(
        self, appointment_id: uuid.UUID, reschedule_in: AppointmentReschedule, user_id: uuid.UUID
    ) -> Appointment:
        """Reschedules an appointment, checking slots conflicts and logging transition states."""
        appointment = await self.appointment_repo.get_with_logs(appointment_id)
        if not appointment:
            raise NotFoundException(message="Appointment not found.")

        # Ownership audit
        if appointment.patient_id != user_id and appointment.doctor_id != user_id:
            raise PermissionException(message="You are not authorized to reschedule this appointment.")

        # State validation
        if appointment.status in ["cancelled", "completed", "no_show"]:
            raise ValidationException(
                message=f"Appointment cannot be rescheduled as it is already marked '{appointment.status}'."
            )

        new_time = reschedule_in.appointment_datetime
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)

        # Check overlapping slots
        is_double_booked = await self.appointment_repo.check_double_booking(
            doctor_id=appointment.doctor_id,
            appointment_datetime=new_time,
            exclude_id=appointment.id,
        )
        if is_double_booked:
            raise ValidationException(
                message="The doctor has another active consultation booked overlapping this time slot."
            )

        old_status = appointment.status
        try:
            appointment.appointment_datetime = new_time
            appointment.availability_id = reschedule_in.availability_id
            appointment.status = "rescheduled"

            await self.appointment_repo.add_status_log(
                appointment_id=appointment.id,
                old_status=old_status,
                new_status="rescheduled",
                changed_by=user_id,
            )
            await self.db.commit()
            return appointment
        except Exception as e:
            await self.db.rollback()
            raise AppException(
                code="RESCHEDULE_FAILED",
                message=f"Failed to reschedule appointment: {str(e)}",
                status_code=500,
            )

    async def rebook_appointment(self, appointment_id: uuid.UUID, user_id: uuid.UUID) -> Appointment:
        """Quick-rebooks an existing appointment details into a new slot (mocked next week)."""
        old_appt = await self.appointment_repo.get(appointment_id)
        if not old_appt:
            raise NotFoundException(message="Original appointment not found.")

        # Clone key consultation info but schedule it exactly 7 days from the old time
        new_time = old_appt.appointment_datetime + timedelta(days=7)
        
        create_schema = AppointmentCreate(
            doctor_id=old_appt.doctor_id,
            availability_id=old_appt.availability_id,
            appointment_datetime=new_time,
            consultation_mode=old_appt.consultation_mode,
            booking_source=old_appt.booking_source,
            symptoms=old_appt.symptoms,
            notes=f"Rebooked from previous appointment {appointment_id}",
        )
        
        return await self.create_appointment(patient_id=user_id, create_in=create_schema)

    async def list_patient_appointments(
        self, patient_id: uuid.UUID, upcoming: bool = True, skip: int = 0, limit: int = 20
    ) -> Tuple[int, List[Appointment]]:
        """List paginated records for patient bookings."""
        return await self.appointment_repo.get_paginated_by_patient(
            patient_id=patient_id, upcoming=upcoming, skip=skip, limit=limit
        )
