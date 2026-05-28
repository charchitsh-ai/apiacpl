from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.models.user import User
from app.schemas.notification import (
    AppointmentReminderRequest,
    EmailNotificationRequest,
    FollowUpReminderRequest,
    NotificationPaginatedResponse,
    NotificationResponse,
    PushNotificationRequest,
    SMSNotificationRequest,
    WhatsAppNotificationRequest,
)
from app.services.notification import NotificationService

# ── Two top-level routers; both registered in v1/__init__.py ──
notify_router = APIRouter(prefix="/notify", tags=["Notifications"])
reminders_router = APIRouter(prefix="/reminders", tags=["Reminders"])
notifications_router = APIRouter(prefix="/notifications", tags=["Notification History"])


# ─────────────────────── Channel Dispatch Endpoints ───────────────────────

@notify_router.post(
    "/whatsapp",
    status_code=status.HTTP_201_CREATED,
    summary="Send a WhatsApp notification via template",
)
async def send_whatsapp(
    request: WhatsAppNotificationRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """
    Renders the named notification template with provided variables and dispatches
    the result to the specified phone number via WhatsApp Business API (mocked).
    """
    notification_service = NotificationService(db)
    notification = await notification_service.send_whatsapp(
        sender_user_id=current_user.id,
        request=request,
    )
    return success_response(
        data=NotificationResponse.model_validate(notification),
        status_code=status.HTTP_201_CREATED,
    )


@notify_router.post(
    "/sms",
    status_code=status.HTTP_201_CREATED,
    summary="Send a raw SMS notification",
)
async def send_sms(
    request: SMSNotificationRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Dispatches a raw SMS message to the specified phone number (mocked)."""
    notification_service = NotificationService(db)
    notification = await notification_service.send_sms(
        sender_user_id=current_user.id,
        request=request,
    )
    return success_response(
        data=NotificationResponse.model_validate(notification),
        status_code=status.HTTP_201_CREATED,
    )


@notify_router.post(
    "/email",
    status_code=status.HTTP_201_CREATED,
    summary="Send an email notification",
)
async def send_email(
    request: EmailNotificationRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Dispatches an email with subject and body to the specified address (mocked)."""
    notification_service = NotificationService(db)
    notification = await notification_service.send_email(
        sender_user_id=current_user.id,
        request=request,
    )
    return success_response(
        data=NotificationResponse.model_validate(notification),
        status_code=status.HTTP_201_CREATED,
    )


@notify_router.post(
    "/push",
    status_code=status.HTTP_201_CREATED,
    summary="Send a push notification to a user",
)
async def send_push(
    request: PushNotificationRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Dispatches a push notification to the target user's registered device (mocked FCM)."""
    notification_service = NotificationService(db)
    notification = await notification_service.send_push(
        sender_user_id=current_user.id,
        request=request,
    )
    return success_response(
        data=NotificationResponse.model_validate(notification),
        status_code=status.HTTP_201_CREATED,
    )


# ─────────────────────── Notification History ───────────────────────

@notifications_router.get(
    "",
    summary="List notification history for the current user",
)
async def list_notifications(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination size"),
    channel: Optional[str] = Query(
        None,
        enum=["whatsapp", "sms", "email", "push"],
        description="Filter by delivery channel",
    ),
    status: Optional[str] = Query(
        None,
        enum=["pending", "sent", "failed"],
        description="Filter by delivery status",
    ),
    notification_type: Optional[str] = Query(
        None,
        description="Filter by notification type (e.g. appointment_booked)",
    ),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Returns paginated notification dispatch history for the logged-in user."""
    notification_service = NotificationService(db)
    total, items = await notification_service.list_user_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        channel=channel,
        status=status,
        notification_type=notification_type,
    )
    paginated = NotificationPaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[NotificationResponse.model_validate(n) for n in items],
    )
    return success_response(data=paginated.model_dump())


# ─────────────────────── Reminder Scheduling ───────────────────────

@reminders_router.post(
    "/appointment",
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an appointment reminder job",
)
async def schedule_appointment_reminder(
    request: AppointmentReminderRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """
    Creates a queued reminder job for a future appointment.
    A background worker processes pending jobs and fires the actual notification.
    Valid reminder_type values: 24h_before, 2h_before, 1h_before, 30min_before.
    """
    notification_service = NotificationService(db)
    job = await notification_service.schedule_appointment_reminder(
        request=request, scheduled_by=current_user.id
    )
    return success_response(
        data={"id": str(job.id), "appointment_id": str(job.appointment_id),
              "reminder_type": job.reminder_type, "scheduled_at": job.scheduled_at.isoformat(),
              "processed": job.processed},
        status_code=status.HTTP_201_CREATED,
    )


@reminders_router.post(
    "/followup",
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a post-consultation follow-up reminder",
)
async def schedule_followup_reminder(
    request: FollowUpReminderRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """
    Creates a queued follow-up reminder job for after a patient's appointment completes.
    Triggered by doctors or system to check-in on patient recovery.
    """
    notification_service = NotificationService(db)
    job = await notification_service.schedule_followup_reminder(
        request=request, scheduled_by=current_user.id
    )
    return success_response(
        data={"id": str(job.id), "appointment_id": str(job.appointment_id),
              "reminder_type": job.reminder_type, "scheduled_at": job.scheduled_at.isoformat(),
              "processed": job.processed},
        status_code=status.HTTP_201_CREATED,
    )
