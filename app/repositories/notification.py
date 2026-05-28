from datetime import datetime, timezone
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification, ReminderJob
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository managing Notification persistence, filtering, and status updates."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Notification, db_session)

    async def get_user_notifications_paginated(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
    ) -> Tuple[int, List[Notification]]:
        """Retrieve paginated notifications for a specific user with optional filters."""
        filters = [Notification.user_id == user_id]

        if channel:
            filters.append(Notification.channel == channel)
        if status:
            filters.append(Notification.status == status)
        if notification_type:
            filters.append(Notification.type == notification_type)

        combined = and_(*filters)
        count_stmt = select(func.count(Notification.id)).filter(combined)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(Notification)
            .filter(combined)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return total, list(result.scalars().all())

    async def mark_sent(self, notification_id: uuid.UUID) -> None:
        """Update a notification record's status to 'sent' and capture sent_at timestamp."""
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(status="sent", sent_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def mark_failed(self, notification_id: uuid.UUID) -> None:
        """Update a notification record's status to 'failed'."""
        await self.db.execute(
            update(Notification).where(Notification.id == notification_id).values(status="failed")
        )
        await self.db.commit()


class ReminderJobRepository(BaseRepository[ReminderJob]):
    """Repository managing ReminderJob scheduling and processed state tracking."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(ReminderJob, db_session)

    async def get_pending_reminders(self) -> List[ReminderJob]:
        """Fetch all unprocessed reminders scheduled to fire at or before now."""
        now = datetime.now(timezone.utc)
        stmt = select(ReminderJob).filter(
            and_(
                ReminderJob.processed == False,  # noqa
                ReminderJob.scheduled_at <= now,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_processed(self, job_id: uuid.UUID) -> None:
        """Mark a reminder job as processed to prevent re-dispatch."""
        await self.db.execute(
            update(ReminderJob).where(ReminderJob.id == job_id).values(processed=True)
        )
        await self.db.commit()
