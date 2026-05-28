import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository managing RefreshToken storage and validation policies."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(RefreshToken, db_session)

    async def get_active_token(self, token: str) -> Optional[RefreshToken]:
        """Fetch a refresh token if it exists, is not revoked, and is not expired."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RefreshToken).filter(
                and_(
                    RefreshToken.token == token,
                    RefreshToken.revoked == False,  # noqa
                    RefreshToken.expires_at > now,
                )
            )
        )
        return result.scalars().first()

    async def revoke_token(self, token: str) -> None:
        """Revoke a single refresh token."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(revoked=True)
        )
        await self.db.commit()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens associated with a specific user."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked=True)
        )
        await self.db.commit()
