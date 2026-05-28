from typing import Any, Generic, List, Optional, TypeVar
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[List[Any]] = []


class StandardResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None


def success_response(data: Any = None, status_code: int = status.HTTP_200_OK) -> JSONResponse:
    """Utility function to return standard success responses."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "error": None,
        },
    )


def error_response(
    code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[List[Any]] = None,
) -> JSONResponse:
    """Utility function to return standard error responses."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers standard handlers for FastAPI to format all errors consistently."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Standardize pydantic validation errors
        details = []
        for error in exc.errors():
            details.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return error_response(
            code="VALIDATION_FAILED",
            message="Input validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "HTTP_ERROR"
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "UNAUTHORIZED"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            code = "FORBIDDEN"
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "NOT_FOUND"

        return error_response(
            code=code,
            message=exc.detail,
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Prevent leaking raw production stack traces, log it locally.
        # In actual system we use structured logger.
        import traceback
        traceback.print_exc()

        return error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
