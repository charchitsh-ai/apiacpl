import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor, DoctorAvailability, DoctorReview
from app.models.speciality import Speciality, doctor_specialities
from app.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    """Repository managing doctor profiles and dynamic advanced filtering pipelines."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(Doctor, db_session)

    async def get_with_relations(self, doctor_id: uuid.UUID) -> Optional[Doctor]:
        """Fetch profile pre-loading specialities, availabilities, and reviews."""
        stmt = (
            select(Doctor)
            .filter(Doctor.id == doctor_id)
            .options(
                selectinload(Doctor.specialities),
                selectinload(Doctor.availabilities),
                selectinload(Doctor.reviews),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def search(self, query_str: str) -> List[Doctor]:
        """Search doctor profiles matching full_name, bio, city or qualifications."""
        stmt = (
            select(Doctor)
            .filter(
                or_(
                    Doctor.full_name.ilike(f"%{query_str}%"),
                    Doctor.bio.ilike(f"%{query_str}%"),
                    Doctor.city.ilike(f"%{query_str}%"),
                    Doctor.qualifications.ilike(f"%{query_str}%"),
                )
            )
            .options(selectinload(Doctor.specialities))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_and_filtered(
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
        """
        Retrieves a paginated list of doctors with advanced SQL filters and counts total match records.
        Optimized using join & selectinload.
        """
        # Base queries
        query = select(Doctor).filter(Doctor.verification_status == "verified")
        count_query = select(func.count(Doctor.id)).filter(Doctor.verification_status == "verified")

        # Filters holder list
        filters = []

        if city:
            filters.append(Doctor.city.ilike(city))
        if language:
            # Query within PostgreSQL JSONB list: e.g. languages ? 'English'
            filters.append(func.jsonb_exists(Doctor.languages, language))
        if min_fee is not None:
            filters.append(Doctor.consultation_fee >= min_fee)
        if max_fee is not None:
            filters.append(Doctor.consultation_fee <= max_fee)
        if telemedicine_enabled is not None:
            filters.append(Doctor.telemedicine_enabled == telemedicine_enabled)
        if clinic_enabled is not None:
            filters.append(Doctor.clinic_enabled == clinic_enabled)
        if min_experience is not None:
            filters.append(Doctor.experience_years >= min_experience)
        if max_experience is not None:
            filters.append(Doctor.experience_years <= max_experience)
        if min_rating is not None:
            filters.append(Doctor.rating >= min_rating)

        # Handle speciality join filter
        if speciality:
            # Join with doctor_specialities and Speciality tables
            speciality_filter = or_(
                Speciality.name.ilike(speciality),
                Speciality.slug == speciality
            )
            query = query.join(Doctor.specialities).filter(speciality_filter)
            count_query = count_query.join(Doctor.specialities).filter(speciality_filter)

        # Apply standard filters
        if filters:
            query = query.filter(and_(*filters))
            count_query = count_query.filter(and_(*filters))

        # Apply sorting
        order_col = Doctor.rating
        if sort_by == "experience":
            order_col = Doctor.experience_years
        elif sort_by == "fee":
            order_col = Doctor.consultation_fee
        elif sort_by == "created_at":
            order_col = Doctor.created_at

        direction = desc if sort_order == "desc" else asc
        query = query.order_by(direction(order_col))

        # Eager load specialities to prevent N+1 queries
        query = query.options(selectinload(Doctor.specialities))

        # Run count and paginated query asynchronously
        total_count_res = await self.db.execute(count_query)
        total_count = total_count_res.scalar_one()

        query = query.offset(skip).limit(limit)
        results_res = await self.db.execute(query)
        items = list(results_res.scalars().all())

        return total_count, items

    async def get_next_available(self, limit: int = 10) -> List[Doctor]:
        """
        Retrieves doctors ordered by active availabilities and rating.
        Prioritizes doctors who have availability slots set up.
        """
        stmt = (
            select(Doctor)
            .filter(and_(Doctor.verification_status == "verified", Doctor.is_available == True))  # noqa
            .join(Doctor.availabilities, isouter=True)
            .order_by(
                desc(Doctor.is_available),
                desc(Doctor.rating),
                desc(Doctor.experience_years),
            )
            .options(selectinload(Doctor.specialities))
            .limit(limit)
            .distinct()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
