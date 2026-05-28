from typing import Any, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.schemas.speciality import SpecialityResponse
from app.services.discovery import DiscoveryService

router = APIRouter(prefix="/specialities", tags=["Specialities"])


@router.get(
    "",
    summary="List specialities with pagination",
)
async def list_specialities(
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(100, ge=1, le=100, description="Pagination limit size"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves all medical disciplines with page limits."""
    discovery_service = DiscoveryService(db)
    specialities = await discovery_service.list_specialities(skip=skip, limit=limit)
    return success_response(
        data=[SpecialityResponse.model_validate(s) for s in specialities]
    )


@router.get(
    "/search",
    summary="Search specialities",
)
async def search_specialities(
    q: str = Query(..., min_length=1, description="Search query string"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Finds medical fields using partial matches on name and description."""
    discovery_service = DiscoveryService(db)
    specialities = await discovery_service.search_specialities(q)
    return success_response(
        data=[SpecialityResponse.model_validate(s) for s in specialities]
    )


@router.get(
    "/{slug}",
    summary="Get speciality details by slug",
)
async def get_speciality(
    slug: str,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Fetch details of a specific medical discipline using its SEO-friendly slug."""
    discovery_service = DiscoveryService(db)
    speciality = await discovery_service.get_speciality_by_slug(slug)
    return success_response(data=SpecialityResponse.model_validate(speciality))
