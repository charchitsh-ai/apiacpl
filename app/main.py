from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config.settings import settings
from app.core.responses import register_exception_handlers

# Initialize production-grade FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade secure healthcare platform for symptom-based doctor discovery, telemedicine, and booking.",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Apply CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register uniform success/error structure exception handlers
register_exception_handlers(app)

# Include API Routers under standard version prefix
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System Health"])
async def health_check():
    """Health check endpoint for containerization/hosting platform checks."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}
