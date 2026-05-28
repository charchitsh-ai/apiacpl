import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core import security
from app.core.exceptions import (
    AuthenticationException,
    DatabaseConflictException,
    NotFoundException,
    ValidationException,
)
from app.models.user import User
from app.models.session import DeviceSession
from app.repositories.otp import OtpRepository
from app.repositories.session import DeviceSessionRepository
from app.repositories.token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserCreate


class AuthService:
    """Business logic service for all authentication, registration, OTP, and session tasks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.otp_repo = OtpRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.session_repo = DeviceSessionRepository(db)

    async def register_user(self, user_in: UserCreate) -> User:
        """Register a new user after verifying uniqueness of phone and email."""
        # 1. Check if email already exists
        existing_email = await self.user_repo.get_by_email(user_in.email)
        if existing_email:
            raise DatabaseConflictException(
                message="A user with this email address already exists."
            )

        # 2. Check if phone already exists
        existing_phone = await self.user_repo.get_by_phone(user_in.phone)
        if existing_phone:
            raise DatabaseConflictException(
                message="A user with this phone number already exists."
            )

        # 3. Hash password and create user
        hashed_password = security.hash_password(user_in.password)
        user_data = user_in.model_dump()
        user_data["hashed_password"] = hashed_password
        user_data.pop("password")

        user = await self.user_repo.create(user_data)
        return user

    async def login_user(
        self,
        login_in: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tuple[str, str, User]:
        """Authenticate user credentials, record the login session, and generate tokens."""
        # 1. Find user by email or phone
        user = await self.user_repo.get_by_username(login_in.username)
        if not user:
            raise AuthenticationException(message="Invalid email/phone or password.")

        # 2. Validate password
        if not security.verify_password(login_in.password, user.hashed_password):
            raise AuthenticationException(message="Invalid email/phone or password.")

        if not user.is_active:
            raise AuthenticationException(message="This account has been deactivated.")

        # 3. Create or update Device Session
        device_name = login_in.device_name or "Unknown Device"
        session = await self.session_repo.get_by_user_and_device(user.id, device_name)
        if session:
            session.ip_address = ip_address
            session.user_agent = user_agent
            await self.session_repo.update_activity(session)
        else:
            await self.session_repo.create(
                {
                    "user_id": user.id,
                    "device_name": device_name,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                }
            )

        # 4. Generate access & refresh tokens
        access_token = security.create_access_token(subject=user.id)
        refresh_token_str = security.create_refresh_token(subject=user.id)

        # 5. Store Refresh Token
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.token_repo.create(
            {
                "user_id": user.id,
                "token": refresh_token_str,
                "expires_at": expires_at,
            }
        )

        return access_token, refresh_token_str, user

    async def logout_user(self, refresh_token: str) -> None:
        """Revoke a refresh token, logging out the user from that session."""
        try:
            decoded = security.decode_token(refresh_token, is_refresh=True)
            user_id = uuid.UUID(decoded["sub"])
        except Exception:
            raise AuthenticationException(message="Invalid or expired refresh token.")

        # Revoke the specific token in DB
        await self.token_repo.revoke_token(refresh_token)

        # Optionally revoke the matching device session if it can be found.
        # For simplicity, we just revoke the refresh token which blocks future token renewals.

    async def refresh_tokens(
        self, refresh_token: str, ip_address: str | None = None, user_agent: str | None = None
    ) -> Tuple[str, str, User]:
        """Verify active refresh token and issue a new set of access/refresh tokens (rotation)."""
        # 1. Decode & validate token format
        try:
            decoded = security.decode_token(refresh_token, is_refresh=True)
            user_id = uuid.UUID(decoded["sub"])
        except Exception:
            raise AuthenticationException(message="Invalid or expired refresh token.")

        # 2. Check if active in DB (revocation check)
        stored_token = await self.token_repo.get_active_token(refresh_token)
        if not stored_token:
            raise AuthenticationException(message="Token is revoked or expired.")

        # 3. Retrieve User
        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationException(message="User is inactive or not found.")

        # 4. Rotate tokens: Revoke old token, generate new pair
        await self.token_repo.revoke_token(refresh_token)

        new_access = security.create_access_token(subject=user.id)
        new_refresh = security.create_refresh_token(subject=user.id)

        # Store new refresh token
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.token_repo.create(
            {
                "user_id": user.id,
                "token": new_refresh,
                "expires_at": expires_at,
            }
        )

        return new_access, new_refresh, user

    async def send_otp(self, phone: str) -> str:
        """Generate, store and dispatch (mocked) a security OTP to user's phone."""
        # 1. Generate 6-digit numeric OTP
        otp_code = "".join(str(random.randint(0, 9)) for _ in range(6))
        # fallback for testing
        if settings.ENVIRONMENT == "development":
            otp_code = "123456"

        # 2. Invalidate previous active OTPs to prevent replay attacks
        await self.otp_repo.invalidate_all_otps(phone)

        # 3. Save OTP with expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.OTP_EXPIRE_MINUTES
        )
        await self.otp_repo.create(
            {
                "phone": phone,
                "otp_code": otp_code,
                "expires_at": expires_at,
            }
        )

        # MOCK DISPATCH (In real system, trigger SMS service like Twilio or MSG91 here)
        # print(f"[SMS DISPATCH MOCK] Sent OTP {otp_code} to {phone}")
        return otp_code

    async def verify_otp(self, phone: str, otp_code: str) -> bool:
        """Validate if the provided OTP code matches an active pending verification record."""
        otp_record = await self.otp_repo.get_active_otp(phone, otp_code)
        if not otp_record:
            raise ValidationException(message="Invalid or expired OTP.")

        # Mark as verified
        otp_record.verified = True
        await self.db.commit()

        # Update user as verified if they exist
        user = await self.user_repo.get_by_phone(phone)
        if user:
            user.is_verified = True
            await self.db.commit()

        return True

    async def forgot_password(self, phone: str) -> str:
        """Initialize password reset flow by verifying user exists and issuing OTP."""
        user = await self.user_repo.get_by_phone(phone)
        if not user:
            raise NotFoundException(message="No account found with this phone number.")

        otp_code = await self.send_otp(phone)
        return otp_code

    async def reset_password(self, reset_in: ResetPasswordRequest) -> None:
        """Verify OTP verification status and set a new hashed password for the user."""
        # Validate that the OTP is correct and verified
        # For security, we require that the OTP has been successfully verified first
        # In a single call, we can check active OTP and consume it:
        otp_record = await self.otp_repo.get_active_otp(reset_in.phone, reset_in.otp_code)
        if not otp_record:
            raise ValidationException(message="Invalid or expired verification code.")

        # Mark OTP verified
        otp_record.verified = True

        # Retrieve user and update password
        user = await self.user_repo.get_by_phone(reset_in.phone)
        if not user:
            raise NotFoundException(message="User not found.")

        user.hashed_password = security.hash_password(reset_in.new_password)
        user.is_verified = True  # Verified by OTP
        await self.db.commit()

    async def get_user_sessions(self, user_id: uuid.UUID) -> List[DeviceSession]:
        """Retrieve all active device login sessions for the current user."""
        return await self.session_repo.get_active_sessions(user_id)
