import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ValidationException
from app.models.notification import Notification, ReminderJob
from app.models.appointment import Appointment
from app.repositories.notification import NotificationRepository, ReminderJobRepository
from app.schemas.notification import (
    AppointmentReminderRequest,
    EmailNotificationRequest,
    FollowUpReminderRequest,
    PushNotificationRequest,
    SMSNotificationRequest,
    WhatsAppNotificationRequest,
)
from app.services.providers import get_provider
from app.utils.template_renderer import TemplateRenderer

logger = logging.getLogger("AYKACare.NotificationService")

# All valid notification type values
VALID_NOTIFICATION_TYPES = frozenset([
    "appointment_booked",
    "appointment_reminder",
    "appointment_cancelled",
    "appointment_rescheduled",
    "prescription_ready",
    "followup_reminder",
    "general",
])

# All valid channel values
VALID_CHANNELS = frozenset(["whatsapp", "sms", "email", "push"])


class NotificationService:
    """
    Central orchestration service for dispatching notifications across all channels.
    Persists audit logs, renders templates, routes to the correct provider, and
    manages reminder job scheduling.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.reminder_repo = ReminderJobRepository(db)
        self.renderer = TemplateRenderer(db)

    # ─────────────────────── Internal helpers ───────────────────────

    async def _persist_notification(
        self,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        channel: str,
        metadata: Dict[str, Any] = None,
    ) -> Notification:
        """Creates and persists a notification record with 'pending' status."""
        return await self.notification_repo.create({
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "channel": channel,
            "status": "pending",
            "metadata_json": metadata or {},
        })

    async def _dispatch(
        self,
        channel: str,
        to: str,
        title: str,
        body: str,
        notification: Notification,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """
        Routes a notification to the correct channel provider and updates the
        persistent log record with 'sent' or 'failed' status.
        """
        try:
            provider = get_provider(channel)
            success = await provider.send(to=to, title=title, body=body, metadata=metadata)
            if success:
                await self.notification_repo.mark_sent(notification.id)
                logger.info(f"Notification {notification.id} dispatched via '{channel}' to '{to}'.")
            else:
                await self.notification_repo.mark_failed(notification.id)
                logger.warning(f"Notification {notification.id} failed via '{channel}'.")
            return success
        except Exception as exc:
            await self.notification_repo.mark_failed(notification.id)
            logger.error(f"Notification {notification.id} error via '{channel}': {exc}", exc_info=True)
            return False

    # ─────────────────────── Channel Dispatchers ───────────────────────

    async def send_whatsapp(
        self,
        sender_user_id: uuid.UUID,
        request: WhatsAppNotificationRequest,
        notification_type: str = "general",
    ) -> Notification:
        """Renders a named template and dispatches a WhatsApp message."""
        subject, rendered_body = await self.renderer.render(
            request.template_name, request.variables
        )
        notification = await self._persist_notification(
            user_id=sender_user_id,
            notification_type=notification_type,
            title=request.template_name,
            message=rendered_body,
            channel="whatsapp",
            metadata={"phone": request.phone, "template": request.template_name},
        )
        await self._dispatch(
            channel="whatsapp",
            to=request.phone,
            title=request.template_name,
            body=rendered_body,
            notification=notification,
        )
        return notification

    async def send_sms(
        self,
        sender_user_id: uuid.UUID,
        request: SMSNotificationRequest,
        notification_type: str = "general",
    ) -> Notification:
        """Dispatches a raw SMS message."""
        notification = await self._persist_notification(
            user_id=sender_user_id,
            notification_type=notification_type,
            title="SMS Alert",
            message=request.message,
            channel="sms",
            metadata={"phone": request.phone},
        )
        await self._dispatch(
            channel="sms",
            to=request.phone,
            title="SMS Alert",
            body=request.message,
            notification=notification,
        )
        return notification

    async def send_email(
        self,
        sender_user_id: uuid.UUID,
        request: EmailNotificationRequest,
        notification_type: str = "general",
    ) -> Notification:
        """Dispatches an email notification."""
        notification = await self._persist_notification(
            user_id=sender_user_id,
            notification_type=notification_type,
            title=request.subject,
            message=request.body,
            channel="email",
            metadata={"email": request.email, "subject": request.subject},
        )
        await self._dispatch(
            channel="email",
            to=request.email,
            title=request.subject,
            body=request.body,
            notification=notification,
            metadata={"subject": request.subject},
        )
        return notification

    async def send_push(
        self,
        sender_user_id: uuid.UUID,
        request: PushNotificationRequest,
        notification_type: str = "general",
    ) -> Notification:
        """Dispatches a push notification to a user by user_id (token resolved at provider level)."""
        notification = await self._persist_notification(
            user_id=request.user_id,
            notification_type=notification_type,
            title=request.title,
            message=request.body,
            channel="push",
            metadata={"target_user_id": str(request.user_id)},
        )
        await self._dispatch(
            channel="push",
            to=str(request.user_id),
            title=request.title,
            body=request.body,
            notification=notification,
        )
        return notification

    # ─────────────────────── Notification Listing ───────────────────────

    async def list_user_notifications(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
    ) -> Tuple[int, List[Notification]]:
        """Returns paginated notification history for a user with optional filters."""
        return await self.notification_repo.get_user_notifications_paginated(
            user_id=user_id,
            skip=skip,
            limit=limit,
            channel=channel,
            status=status,
            notification_type=notification_type,
        )

    # ─────────────────────── Reminder Scheduling ───────────────────────

    async def schedule_appointment_reminder(
        self, request: AppointmentReminderRequest, scheduled_by: uuid.UUID
    ) -> ReminderJob:
        """
        Persists an appointment reminder job for background queue processing.
        The queue worker (cron / Celery / ARQ) picks up unprocessed jobs and
        dispatches the actual notification at the scheduled time.
        """
        # Validate appointment exists
        appt_stmt = select(Appointment).filter(Appointment.id == request.appointment_id)
        appt_res = await self.db.execute(appt_stmt)
        appointment = appt_res.scalars().first()
        if not appointment:
            raise NotFoundException(message="Appointment not found for reminder scheduling.")

        valid_types = ["24h_before", "2h_before", "1h_before", "30min_before"]
        if request.reminder_type not in valid_types:
            raise ValidationException(
                message=f"reminder_type must be one of: {valid_types}"
            )

        job = await self.reminder_repo.create({
            "appointment_id": request.appointment_id,
            "reminder_type": request.reminder_type,
            "scheduled_at": request.scheduled_at,
            "processed": False,
        })

        logger.info(
            f"Reminder job {job.id} scheduled for appointment {request.appointment_id} "
            f"at {request.scheduled_at} (type: {request.reminder_type})"
        )
        return job

    async def schedule_followup_reminder(
        self, request: FollowUpReminderRequest, scheduled_by: uuid.UUID
    ) -> ReminderJob:
        """
        Persists a post-consultation follow-up reminder job.
        Triggers a 'followup_reminder' notification for the patient after their appointment.
        """
        appt_stmt = select(Appointment).filter(Appointment.id == request.appointment_id)
        appt_res = await self.db.execute(appt_stmt)
        appointment = appt_res.scalars().first()
        if not appointment:
            raise NotFoundException(message="Appointment not found for follow-up scheduling.")

        job = await self.reminder_repo.create({
            "appointment_id": request.appointment_id,
            "reminder_type": "followup_reminder",
            "scheduled_at": request.scheduled_at,
            "processed": False,
        })

        logger.info(
            f"Follow-up reminder job {job.id} scheduled for appointment "
            f"{request.appointment_id} at {request.scheduled_at}"
        )
        return job

    # ─────────────────────── Queue Worker Hook (ready for Celery/ARQ) ──────────

    async def process_pending_reminders(self) -> int:
        """
        Fetches all unprocessed reminder jobs due now and fires notifications.
        This method is designed to be called by a background task scheduler
        (e.g., Celery beat, ARQ, APScheduler) periodically.
        Returns the count of jobs processed.
        """
        pending = await self.reminder_repo.get_pending_reminders()
        processed_count = 0

        for job in pending:
            try:
                # Load the associated appointment
                appt_stmt = select(Appointment).filter(Appointment.id == job.appointment_id)
                appt_res = await self.db.execute(appt_stmt)
                appointment = appt_res.scalars().first()

                if not appointment:
                    await self.reminder_repo.mark_processed(job.id)
                    continue

                # Render a generic inline message
                msg = (
                    f"Reminder: Your appointment is scheduled. Type: {job.reminder_type}"
                    if job.reminder_type != "followup_reminder"
                    else "Follow-up reminder: How are you feeling after your consultation?"
                )

                # Persist notification for patient
                notification = await self._persist_notification(
                    user_id=appointment.patient_id,
                    notification_type=(
                        "appointment_reminder"
                        if job.reminder_type != "followup_reminder"
                        else "followup_reminder"
                    ),
                    title="AYKA Care Reminder",
                    message=msg,
                    channel="sms",  # Default channel; extend per user preferences
                    metadata={"appointment_id": str(appointment.id), "reminder_type": job.reminder_type},
                )

                # Dispatch (SMS default)
                provider = get_provider("sms")
                await provider.send(to="", title="AYKA Care Reminder", body=msg)
                await self.notification_repo.mark_sent(notification.id)

                # Mark job processed
                await self.reminder_repo.mark_processed(job.id)
                processed_count += 1
                logger.info(f"Processed reminder job {job.id} for appointment {job.appointment_id}.")

            except Exception as exc:
                logger.error(f"Failed to process reminder job {job.id}: {exc}", exc_info=True)

        return processed_count
