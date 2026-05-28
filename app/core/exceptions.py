from typing import Any, List, Optional
from fastapi import HTTPException, status


class AppException(Exception):
    """Base application exception for custom error management."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[List[Any]] = None):
        super().__init__(
            code="UNAUTHENTICATED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionException(AppException):
    def __init__(self, message: str = "Permission denied", details: Optional[List[Any]] = None):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[List[Any]] = None):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[List[Any]] = None):
        super().__init__(
            code="VALIDATION_FAILED",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class DatabaseConflictException(AppException):
    def __init__(self, message: str = "Resource already exists", details: Optional[List[Any]] = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )
