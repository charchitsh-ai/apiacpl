from typing import Any, List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.responses import success_response
from app.models.user import User
from app.schemas.auth import (
    DeviceSessionResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    user_in: UserCreate, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Creates a new patient/doctor/admin record in the system."""
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_in)
    return success_response(
        data=UserResponse.model_validate(user),
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/login",
    summary="Authenticate credentials and issue tokens",
)
async def login(
    request: Request,
    login_in: LoginRequest,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Logs in user, creates a device session registry, and issues security tokens."""
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, refresh_token, user = await auth_service.login_user(
        login_in, ip_address=ip_address, user_agent=user_agent
    )

    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )
    return success_response(data=token_data.model_dump())


@router.post(
    "/logout",
    summary="Log out of current device session",
)
async def logout(
    refresh_in: RefreshTokenRequest, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Revokes the refresh token to prevent further access token renewals."""
    auth_service = AuthService(db)
    await auth_service.logout_user(refresh_in.refresh_token)
    return success_response(data={"message": "Successfully logged out from session."})


@router.post(
    "/send-otp",
    summary="Generate and dispatch SMS verification OTP",
)
async def send_otp(
    otp_in: SendOtpRequest, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Sends a 6-digit verification code to the phone number (returns 123456 in development)."""
    auth_service = AuthService(db)
    otp_code = await auth_service.send_otp(otp_in.phone)
    return success_response(
        data={
            "message": "OTP code dispatched successfully.",
            # Only returned in response for development purposes
            "otp_code_preview": otp_code,
        }
    )


@router.post(
    "/verify-otp",
    summary="Verify phone ownership using OTP",
)
async def verify_otp(
    verify_in: VerifyOtpRequest, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Validates the OTP code, setting the user is_verified status as true."""
    auth_service = AuthService(db)
    await auth_service.verify_otp(verify_in.phone, verify_in.otp_code)
    return success_response(data={"message": "Phone number successfully verified."})


@router.post(
    "/forgot-password",
    summary="Initialize forgotten password reset",
)
async def forgot_password(
    forgot_in: ForgotPasswordRequest, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Generates a security OTP code for authenticated password reset authorization."""
    auth_service = AuthService(db)
    otp_code = await auth_service.forgot_password(forgot_in.phone)
    return success_response(
        data={
            "message": "Password reset code successfully dispatched.",
            "otp_code_preview": otp_code,
        }
    )


@router.post(
    "/reset-password",
    summary="Reset password using OTP",
)
async def reset_password(
    reset_in: ResetPasswordRequest, db: AsyncSession = Depends(deps.get_db_session)
) -> Any:
    """Validates OTP verification and sets the new strong password."""
    auth_service = AuthService(db)
    await auth_service.reset_password(reset_in)
    return success_response(data={"message": "Password reset successfully completed."})


@router.post(
    "/refresh-token",
    summary="Rotate expired access and refresh tokens",
)
async def refresh_token(
    request: Request,
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Rotates refresh tokens and issues fresh access token."""
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, new_refresh_token, user = await auth_service.refresh_tokens(
        refresh_in.refresh_token, ip_address=ip_address, user_agent=user_agent
    )

    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )
    return success_response(data=token_data.model_dump())


@router.get(
    "/sessions",
    summary="Get user's logged in active sessions",
)
async def get_sessions(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db_session),
) -> Any:
    """Lists all active device sessions logged in for the current authenticated user."""
    auth_service = AuthService(db)
    sessions = await auth_service.get_user_sessions(current_user.id)
    return success_response(
        data=[DeviceSessionResponse.model_validate(s) for s in sessions]
    )
