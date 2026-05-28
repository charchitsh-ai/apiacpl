import logging
from typing import Any, Dict
from app.services.providers.base import BaseNotificationProvider

logger = logging.getLogger("AYKACare.SMSProvider")


class SMSProvider(BaseNotificationProvider):
    """SMS Notification Provider ready for MSG91 / Twilio SMS API integration."""

    async def send(self, to: str, title: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        # Mock SMS dispatch (plug in MSG91 or Twilio here)
        logger.info(
            f"[SMS DISPATCH MOCK] Sending SMS to '{to}':"
            f"\n  Message: {body}"
            f"\n  Metadata: {metadata}"
        )
        return True
