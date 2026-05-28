import logging
from typing import Any, Dict
from app.services.providers.base import BaseNotificationProvider

logger = logging.getLogger("AYKACare.WhatsAppProvider")


class WhatsAppProvider(BaseNotificationProvider):
    """WhatsApp Notification Provider ready for WhatsApp Business API integration."""

    async def send(self, to: str, title: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        # Mocking WhatsApp dispatch (ready to plug in Twilio WhatsApp or Meta Business API)
        logger.info(
            f"[WHATSAPP DISPATCH MOCK] Dispatching to '{to}':"
            f"\n  Template/Title: {title}"
            f"\n  Message: {body}"
            f"\n  Metadata: {metadata}"
        )
        return True
