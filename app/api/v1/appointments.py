from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentPaginatedResponse,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.services.booking import BookingService

router = APIRouter(prefix="/appointments", tags=["Appointments & Booking"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Book a new doctor appointment slot",
)
async def create_appointment(
    create_in: AppointmentCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """
    Schedules a clinical consultation slot.
    Checks doctor calendars, validates availability, and prevents overlapping double-bookings.
    """
    booking_service = BookingService(db)
    appointment = await booking_service.create_appointment(
        patient_id=current_user.id, create_in=create_in
    )
    return success_response(
        data=AppointmentResponse.model_validate(appointment),
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/upcoming",
    summary="Get upcoming active appointments",
)
async def list_upcoming_appointments(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=50, description="Pagination size"),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Lists upcoming consultations for the logged-in user with active states (booked/confirmed)."""
    booking_service = BookingService(db)
    total, items = await booking_service.list_patient_appointments(
        patient_id=current_user.id, upcoming=True, skip=skip, limit=limit
    )
    paginated_data = AppointmentPaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[AppointmentResponse.model_validate(item) for item in items]
    )
    return success_response(data=paginated_data.model_dump())


@router.get(
    "/history",
    summary="Get historical past/cancelled appointments",
)
async def list_historical_appointments(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=50, description="Pagination size"),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Lists past or terminated bookings (cancelled/completed/no-show)."""
    booking_service = BookingService(db)
    total, items = await booking_service.list_patient_appointments(
        patient_id=current_user.id, upcoming=False, skip=skip, limit=limit
    )
    paginated_data = AppointmentPaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[AppointmentResponse.model_validate(item) for item in items]
    )
    return success_response(data=paginated_data.model_dump())


@router.post(
    "/rebook",
    summary="Quickly duplicate a previous booking",
)
async def rebook_appointment(
    appointment_id: uuid.UUID = Query(..., description="The ID of the previous appointment to duplicate"),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Quickly duplicates patient, doctor, mode, and symptoms fields into a slot next week."""
    booking_service = BookingService(db)
    appointment = await booking_service.rebook_appointment(
        appointment_id=appointment_id, user_id=current_user.id
    )
    return success_response(data=AppointmentResponse.model_validate(appointment))


@router.get(
    "/{appointment_id}",
    summary="Get appointment details by ID",
)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves full details of an appointment, tracking transition logs."""
    booking_service = BookingService(db)
    appointment = await booking_service.get_appointment(
        appointment_id=appointment_id, user_id=current_user.id
    )
    return success_response(data=AppointmentResponse.model_validate(appointment))


@router.patch(
    "/{appointment_id}",
    summary="Partially update appointment details",
)
async def update_appointment(
    appointment_id: uuid.UUID,
    update_in: AppointmentUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Partially updates notes or logs transition statuses for the appointment."""
    booking_service = BookingService(db)
    # Re-use standard get flow for ownership audit
    appointment = await booking_service.get_appointment(
        appointment_id=appointment_id, user_id=current_user.id
    )
    
    old_status = appointment.status
    if update_in.notes is not None:
        appointment.notes = update_in.notes
        
    if update_in.status is not None and update_in.status != old_status:
        appointment.status = update_in.status
        await booking_service.appointment_repo.add_status_log(
            appointment_id=appointment.id,
            old_status=old_status,
            new_status=update_in.status,
            changed_by=current_user.id,
        )
        
    await db.commit()
    return success_response(data=AppointmentResponse.model_validate(appointment))


@router.post(
    "/{appointment_id}/cancel",
    summary="Cancel active appointment slot",
)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Cancels booking, updates state, and appends audit logs."""
    booking_service = BookingService(db)
    appointment = await booking_service.cancel_appointment(
        appointment_id=appointment_id, user_id=current_user.id
    )
    return success_response(data=AppointmentResponse.model_validate(appointment))


@router.post(
    "/{appointment_id}/reschedule",
    summary="Reschedule active appointment slot",
)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    reschedule_in: AppointmentReschedule,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Updates appointment datetime, maps new schedules, and verifies slot conflicts."""
    booking_service = BookingService(db)
    appointment = await booking_service.reschedule_appointment(
        appointment_id=appointment_id,
        reschedule_in=reschedule_in,
        user_id=current_user.id,
    )
    return success_response(data=AppointmentResponse.model_validate(appointment))
