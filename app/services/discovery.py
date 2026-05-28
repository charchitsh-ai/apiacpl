from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.doctor import Doctor
from app.models.symptom import Symptom
from app.models.speciality import Speciality
from app.repositories.symptom import SymptomRepository
from app.repositories.speciality import SpecialityRepository


class DiscoveryService:
    """Service layer executing clinical search, mapping mapping, and doctor discovery query pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.symptom_repo = SymptomRepository(db)
        self.speciality_repo = SpecialityRepository(db)

    # Symptom operations
    async def search_symptoms(self, q: str) -> List[Symptom]:
        """Search symptoms using case-insensitive matches."""
        return await self.symptom_repo.search(q)

    async def get_symptom(self, symptom_id: uuid.UUID) -> Symptom:
        """Fetch a specific symptom; raises NotFoundException if missing."""
        symptom = await self.symptom_repo.get(symptom_id)
        if not symptom:
            raise NotFoundException(message="Symptom not found with the requested ID.")
        return symptom

    async def get_symptom_specialities(self, symptom_id: uuid.UUID) -> List[Speciality]:
        """Retrieve all medical specialities mapped to a specific clinical symptom."""
        symptom = await self.symptom_repo.get_with_specialities(symptom_id)
        if not symptom:
            raise NotFoundException(message="Symptom not found with the requested ID.")
        return symptom.specialities

    # Speciality operations
    async def list_specialities(self, skip: int = 0, limit: int = 100) -> List[Speciality]:
        """Fetch specialities with offset and limit pagination parameters."""
        return await self.speciality_repo.get_all_with_pagination(skip=skip, limit=limit)

    async def get_speciality_by_slug(self, slug: str) -> Speciality:
        """Fetch a single speciality by its unique URL slug."""
        speciality = await self.speciality_repo.get_by_slug(slug)
        if not speciality:
            raise NotFoundException(message="Speciality not found with the requested slug.")
        return speciality

    async def search_specialities(self, q: str) -> List[Speciality]:
        """Search specialities using case-insensitive mapping filters."""
        return await self.speciality_repo.search(q)

    # Doctor discovery pipeline
    async def discover_doctors_by_symptom(self, symptom_id: uuid.UUID) -> List[Doctor]:
        """
        Executes a highly optimized database join query:
        1. Joins Doctors -> doctor_specialities -> Speciality -> symptom_speciality_map -> Symptom
        2. Filters by target Symptom ID
        3. Loads doctor specialities eagerly to prevent N+1 lazy loading queries.
        """
        # First ensure the symptom exists
        await self.get_symptom(symptom_id)

        # Single optimized async join
        stmt = (
            select(Doctor)
            .join(Doctor.specialities)
            .join(Speciality.symptoms)
            .filter(Symptom.id == symptom_id)
            .filter(Doctor.verification_status == "verified")
            .options(selectinload(Doctor.specialities))
            .distinct()
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

