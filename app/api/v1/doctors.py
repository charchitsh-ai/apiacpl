from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.schemas.doctor_profile import DoctorProfileResponse, DoctorPaginatedResponse
from app.schemas.availability import AvailabilityResponse
from app.schemas.review import ReviewResponse
from app.services.doctor import DoctorService
from app.services.discovery import DiscoveryService

router = APIRouter(prefix="/doctors", tags=["Doctors & Discovery"])


@router.get(
    "",
    summary="List doctors with pagination and dynamic filtering",
)
async def list_doctors(
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit size"),
    city: str | None = Query(None, description="Filter by city name"),
    language: str | None = Query(None, description="Filter by spoken language"),
    speciality: str | None = Query(None, description="Filter by speciality name or slug"),
    min_fee: float | None = Query(None, ge=0.0, description="Minimum consultation fee"),
    max_fee: float | None = Query(None, ge=0.0, description="Maximum consultation fee"),
    telemedicine_enabled: bool | None = Query(None, description="Filter telemedicine status"),
    clinic_enabled: bool | None = Query(None, description="Filter in-person clinic consultation status"),
    min_experience: int | None = Query(None, ge=0, description="Minimum experience in years"),
    max_experience: int | None = Query(None, ge=0, description="Maximum experience in years"),
    min_rating: float | None = Query(None, ge=1.0, le=5.0, description="Minimum rating"),
    sort_by: str | None = Query("rating", enum=["rating", "experience", "fee", "created_at"], description="Sort field"),
    sort_order: str | None = Query("desc", enum=["asc", "desc"], description="Sort direction"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Lists verified doctor profiles matching filtered criteria."""
    doctor_service = DoctorService(db)
    total, items = await doctor_service.list_doctors_paginated(
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
    
    paginated_data = DoctorPaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[DoctorProfileResponse.model_validate(item) for item in items]
    )
    return success_response(data=paginated_data.model_dump())


@router.get(
    "/search",
    summary="Search doctors by keyword",
)
async def search_doctors(
    q: str = Query(..., min_length=1, description="Keyword search query"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Finds doctors matching query keywords in name, bio, city, or qualifications."""
    doctor_service = DoctorService(db)
    doctors = await doctor_service.search_doctors(q)
    return success_response(
        data=[DoctorProfileResponse.model_validate(d) for d in doctors]
    )


@router.get(
    "/next-available",
    summary="Get doctors ordered by upcoming availabilities",
)
async def next_available_doctors(
    limit: int = Query(10, ge=1, le=50, description="Limit count"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves verified doctors prioritized by active availability calendars."""
    doctor_service = DoctorService(db)
    doctors = await doctor_service.get_next_available_doctors(limit=limit)
    return success_response(
        data=[DoctorProfileResponse.model_validate(d) for d in doctors]
    )


@router.get(
    "/by-symptom/{symptom_id}",
    summary="Discover active doctors by clinical symptom ID",
)
async def discover_doctors_by_symptom(
    symptom_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """
    Executes a scalable discovery search flow:
    Clinical Symptom -> Mapped Specialities -> Active Doctors.
    """
    discovery_service = DiscoveryService(db)
    doctors = await discovery_service.discover_doctors_by_symptom(symptom_id)
    return success_response(
        data=[DoctorProfileResponse.model_validate(d) for d in doctors]
    )


@router.get(
    "/{doctor_id}",
    summary="Get doctor profile details",
)
async def get_doctor_profile(
    doctor_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves full details of a doctor profile by ID, preloading relations."""
    doctor_service = DoctorService(db)
    doctor = await doctor_service.get_doctor_profile(doctor_id)
    return success_response(data=DoctorProfileResponse.model_validate(doctor))


@router.get(
    "/{doctor_id}/availability",
    summary="Get doctor availability calendar",
)
async def get_doctor_availability(
    doctor_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Lists weekly availability consultation slots for a doctor."""
    doctor_service = DoctorService(db)
    availabilities = await doctor_service.get_doctor_availability(doctor_id)
    return success_response(
        data=[AvailabilityResponse.model_validate(a) for a in availabilities]
    )


@router.get(
    "/{doctor_id}/reviews",
    summary="Get doctor ratings and reviews",
)
async def get_doctor_reviews(
    doctor_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves history of patient reviews and ratings for a doctor."""
    doctor_service = DoctorService(db)
    reviews = await doctor_service.get_doctor_reviews(doctor_id)
    return success_response(
        data=[ReviewResponse.model_validate(r) for r in reviews]
    )
