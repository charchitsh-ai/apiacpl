from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.symptom import Symptom
from app.repositories.base import BaseRepository


class SymptomRepository(BaseRepository[Symptom]):
    """Repository managing Symptom database operations."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Symptom, db_session)

    async def search(self, query_str: str) -> List[Symptom]:
        """Search symptoms by name or description using partial, case-insensitive matches."""
        # Convert string to lowercase for PG ilike equivalent or lower function
        stmt = select(Symptom).filter(
            Symptom.name.ilike(f"%{query_str}%") | Symptom.description.ilike(f"%{query_str}%")
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_specialities(self, symptom_id: uuid.UUID) -> Optional[Symptom]:
        """Retrieve a symptom along with its mapped medical specialities using optimized selectinload."""
        stmt = (
            select(Symptom)
            .filter(Symptom.id == symptom_id)
            .options(selectinload(Symptom.specialities))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
