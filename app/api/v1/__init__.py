from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.symptoms import router as symptoms_router
from app.api.v1.specialities import router as specialities_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.notify import notify_router, reminders_router, notifications_router

api_router = APIRouter()

# Module routers
api_router.include_router(auth_router)
api_router.include_router(symptoms_router)
api_router.include_router(specialities_router)
api_router.include_router(doctors_router)
api_router.include_router(appointments_router)

# Notification module routers
api_router.include_router(notify_router)
api_router.include_router(notifications_router)
api_router.include_router(reminders_router)
