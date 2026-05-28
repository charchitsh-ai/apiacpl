from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.otp import OtpVerification
from app.repositories.base import BaseRepository


class OtpRepository(BaseRepository[OtpVerification]):
    """Repository managing OTP verification cycles."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(OtpVerification, db_session)

    async def get_active_otp(self, phone: str, otp_code: str) -> Optional[OtpVerification]:
        """Fetch a matching unverified and non-expired OTP record."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(OtpVerification).filter(
                and_(
                    OtpVerification.phone == phone,
                    OtpVerification.otp_code == otp_code,
                    OtpVerification.verified == False,  # noqa
                    OtpVerification.expires_at > now,
                )
            )
        )
        return result.scalars().first()

    async def invalidate_all_otps(self, phone: str) -> None:
        """Invalidate all previous OTPs sent to a phone number to enforce security."""
        await self.db.execute(
            update(OtpVerification)
            .where(OtpVerification.phone == phone)
            .values(verified=True)
        )
        await self.db.commit()
