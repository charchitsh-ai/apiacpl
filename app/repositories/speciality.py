from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.speciality import Speciality
from app.repositories.base import BaseRepository


class SpecialityRepository(BaseRepository[Speciality]):
    """Repository managing Speciality database operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Speciality, db_session)

    async def get_by_slug(self, slug: str) -> Optional[Speciality]:
        """Fetch a single speciality by its SEO-friendly slug."""
        stmt = select(Speciality).filter(Speciality.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def search(self, query_str: str) -> List[Speciality]:
        """Search medical specialities by name or description using case-insensitive mapping."""
        stmt = select(Speciality).filter(
            Speciality.name.ilike(f"%{query_str}%") | Speciality.description.ilike(f"%{query_str}%")
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_pagination(self, skip: int = 0, limit: int = 100) -> List[Speciality]:
        """Retrieve all specialities with limit and skip offsets."""
        stmt = select(Speciality).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
