from datetime import datetime, timedelta, timezone
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment, AppointmentStatusLog
from app.repositories.base import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    """Repository managing Appointment models, conflict validations, and status change logs."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Appointment, db_session)

    async def get_with_logs(self, appointment_id: uuid.UUID) -> Optional[Appointment]:
        """Retrieve appointment profile along with its historical status logs."""
        stmt = (
            select(Appointment)
            .filter(Appointment.id == appointment_id)
            .options(
                selectinload(Appointment.status_logs).selectinload(AppointmentStatusLog.modifier),
                selectinload(Appointment.doctor),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def check_double_booking(
        self, doctor_id: uuid.UUID, appointment_datetime: datetime, exclude_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Prevents double bookings by checking for overlapping active appointments.
        Overlaps are defined as slots occurring within a standard 30-minute consultation window.
        Active appointments have status in ['booked', 'confirmed', 'rescheduled'].
        """
        # Standard consultation duration is 30 minutes
        slot_duration = timedelta(minutes=30)
        start_time = appointment_datetime - slot_duration + timedelta(seconds=1)
        end_time = appointment_datetime + slot_duration - timedelta(seconds=1)

        active_statuses = ["booked", "confirmed", "rescheduled"]

        stmt = select(Appointment).filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(active_statuses),
                Appointment.appointment_datetime.between(start_time, end_time),
            )
        )

        if exclude_id:
            stmt = stmt.filter(Appointment.id != exclude_id)

        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def add_status_log(
        self, appointment_id: uuid.UUID, old_status: str, new_status: str, changed_by: Optional[uuid.UUID]
    ) -> AppointmentStatusLog:
        """Appends a audit log tracking status transitions."""
        log_obj = AppointmentStatusLog(
            appointment_id=appointment_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        self.db.add(log_obj)
        # Session commit is handled by the wrapping transactional Service layer
        return log_obj

    async def get_paginated_by_patient(
        self, patient_id: uuid.UUID, upcoming: bool = True, skip: int = 0, limit: int = 20
    ) -> Tuple[int, List[Appointment]]:
        """Lists appointments for a patient, split by upcoming vs history, with pagination."""
        now = datetime.now(timezone.utc)
        
        # Define condition for upcoming vs historical
        if upcoming:
            time_cond = Appointment.appointment_datetime >= now
            # Upcoming includes active states: booked, confirmed, rescheduled
            state_cond = Appointment.status.in_(["booked", "confirmed", "rescheduled"])
            order_by_col = Appointment.appointment_datetime.asc()
        else:
            # History includes past datetimes OR terminated states: cancelled, completed, no_show
            time_cond = Appointment.appointment_datetime < now
            state_cond = Appointment.status.in_(["cancelled", "completed", "no_show"])
            order_by_col = Appointment.appointment_datetime.desc()

        base_stmt = select(Appointment).filter(Appointment.patient_id == patient_id)
        
        # Combine filters
        combined_filter = and_(
            Appointment.patient_id == patient_id,
            or_(time_cond, state_cond)
        )

        query = base_stmt.filter(combined_filter).order_by(order_by_col).options(
            selectinload(Appointment.status_logs),
            selectinload(Appointment.doctor),
        )
        count_query = select(func.count(Appointment.id)).filter(combined_filter)

        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one()

        query = query.offset(skip).limit(limit)
        results = await self.db.execute(query)
        items = list(results.scalars().all())

        return total, items
