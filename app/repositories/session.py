import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.session import DeviceSession
from app.repositories.base import BaseRepository


class DeviceSessionRepository(BaseRepository[DeviceSession]):
    """Repository managing user logins and multi-device sessions."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(DeviceSession, db_session)

    async def get_active_sessions(self, user_id: uuid.UUID) -> List[DeviceSession]:
        """Fetch all registered active device sessions for a user."""
        result = await self.db.execute(
            select(DeviceSession)
            .filter(DeviceSession.user_id == user_id)
            .order_back(DeviceSession.last_active_at)  # Order by latest active first
            if hasattr(DeviceSession, "order_back")
            else select(DeviceSession)
            .filter(DeviceSession.user_id == user_id)
            .order_by(DeviceSession.last_active_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_device(
        self, user_id: uuid.UUID, device_name: str
    ) -> Optional[DeviceSession]:
        """Find an existing device session by user and device name."""
        result = await self.db.execute(
            select(DeviceSession).filter(
                and_(DeviceSession.user_id == user_id, DeviceSession.device_name == device_name)
            )
        )
        return result.scalars().first()

    async def update_activity(self, session: DeviceSession) -> DeviceSession:
        """Refresh the last active timestamp for a user session."""
        session.last_active_at = datetime.now(timezone.utc)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def remove_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        """Revoke a specific device session for a user."""
        result = await self.db.execute(
            delete(DeviceSession).where(
                and_(DeviceSession.id == session_id, DeviceSession.user_id == user_id)
            )
        )
        await self.db.commit()
        return result.rowcount > 0
