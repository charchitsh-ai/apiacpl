from typing import List, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException
from app.models.doctor import Doctor, DoctorAvailability, DoctorReview
from app.repositories.doctor import DoctorRepository


class DoctorService:
    """Service layer coordinating advanced clinical discovery queries and availability checks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doctor_repo = DoctorRepository(db)

    async def list_doctors_paginated(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        city: str | None = None,
        language: str | None = None,
        speciality: str | None = None,
        min_fee: float | None = None,
        max_fee: float | None = None,
        telemedicine_enabled: bool | None = None,
        clinic_enabled: bool | None = None,
        min_experience: int | None = None,
        max_experience: int | None = None,
        min_rating: float | None = None,
        sort_by: str | None = "rating",
        sort_order: str | None = "desc",
    ) -> Tuple[int, List[Doctor]]:
        """List and dynamically filter active doctor profiles."""
        return await self.doctor_repo.get_paginated_and_filtered(
            skip=skip,
            limit=limit,
            city=city,
            language=language,
            speciality=speciality,
            min_fee=min_fee,
            max_fee=max_fee,
            telemedicine_enabled=telemedicine_enabled,
            clinic_enabled=clinic_enabled,
            min_experience=min_experience,
            max_experience=max_experience,
            min_rating=min_rating,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def search_doctors(self, q: str) -> List[Doctor]:
        """Search doctors using query keywords."""
        return await self.doctor_repo.search(q)

    async def get_doctor_profile(self, doctor_id: uuid.UUID) -> Doctor:
        """Fetch doctor profile; raises NotFoundException if missing."""
        doctor = await self.doctor_repo.get_with_relations(doctor_id)
        if not doctor:
            raise NotFoundException(message="Doctor profile not found with the requested ID.")
        return doctor

    async def get_doctor_availability(self, doctor_id: uuid.UUID) -> List[DoctorAvailability]:
        """Fetch daily availability schedule for a doctor."""
        # Validate doctor exists
        await self.get_doctor_profile(doctor_id)
        
        stmt = (
            select(DoctorAvailability)
            .filter(DoctorAvailability.doctor_id == doctor_id)
            .order_by(DoctorAvailability.day_of_week.asc(), DoctorAvailability.start_time.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_doctor_reviews(self, doctor_id: uuid.UUID) -> List[DoctorReview]:
        """Fetch patient reviews and ratings for a doctor."""
        # Validate doctor exists
        await self.get_doctor_profile(doctor_id)

        stmt = (
            select(DoctorReview)
            .filter(DoctorReview.doctor_id == doctor_id)
            .order_by(DoctorReview.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_next_available_doctors(self, limit: int = 10) -> List[Doctor]:
        """Fetch doctors prioritized by instant availability indicators."""
        return await self.doctor_repo.get_next_available(limit=limit)
