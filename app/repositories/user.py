from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository managing User model data access operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(User, db_session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email."""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Fetch a user by phone number."""
        result = await self.db.execute(select(User).filter(User.phone == phone))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by either email or phone number."""
        result = await self.db.execute(
            select(User).filter(or_(User.email == username, User.phone == username))
        )
        return result.scalars().first()
