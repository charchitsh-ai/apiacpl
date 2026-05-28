import logging
from typing import Any, Dict
from app.services.providers.base import BaseNotificationProvider

logger = logging.getLogger("AYKACare.EmailProvider")


class EmailProvider(BaseNotificationProvider):
    """Email Notification Provider ready for SendGrid / AWS SES / SMTP integration."""

    async def send(self, to: str, title: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        # Mock Email dispatch (plug in SendGrid, SES, or aiosmtplib here)
        subject = (metadata or {}).get("subject", title)
        logger.info(
            f"[EMAIL DISPATCH MOCK] Sending Email to '{to}':"
            f"\n  Subject: {subject}"
            f"\n  Body: {body[:120]}..."
            f"\n  Metadata: {metadata}"
        )
        return True
