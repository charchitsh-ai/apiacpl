from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.schemas.symptom import SymptomResponse
from app.schemas.speciality import SpecialityResponse
from app.services.discovery import DiscoveryService

router = APIRouter(prefix="/symptoms", tags=["Symptoms"])


@router.get(
    "/search",
    summary="Search symptoms",
)
async def search_symptoms(
    q: str = Query(..., min_length=1, description="Search query string"),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Finds clinical symptoms using partial matches on name and description."""
    discovery_service = DiscoveryService(db)
    symptoms = await discovery_service.search_symptoms(q)
    return success_response(
        data=[SymptomResponse.model_validate(s) for s in symptoms]
    )


@router.get(
    "/{symptom_id}",
    summary="Get symptom details",
)
async def get_symptom(
    symptom_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Fetch profile information for a specific symptom by its UUID."""
    discovery_service = DiscoveryService(db)
    symptom = await discovery_service.get_symptom(symptom_id)
    return success_response(data=SymptomResponse.model_validate(symptom))


@router.get(
    "/{symptom_id}/specialities",
    summary="Get mapped specialities for symptom",
)
async def get_symptom_specialities(
    symptom_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Retrieves all medical specialities mapped to resolve this clinical symptom."""
    discovery_service = DiscoveryService(db)
    specialities = await discovery_service.get_symptom_specialities(symptom_id)
    return success_response(
        data=[SpecialityResponse.model_validate(s) for s in specialities]
    )
