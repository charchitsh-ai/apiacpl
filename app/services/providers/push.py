import logging
from typing import Any, Dict
from app.services.providers.base import BaseNotificationProvider

logger = logging.getLogger("AYKACare.PushProvider")


class PushProvider(BaseNotificationProvider):
    """Push Notification Provider ready for Firebase FCM / Apple APNs integration."""

    async def send(self, to: str, title: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        # Mock Push dispatch (plug in firebase-admin FCM or APNs here)
        # `to` here is expected to be the device token or user_id
        logger.info(
            f"[PUSH DISPATCH MOCK] Sending Push to device token/user '{to}':"
            f"\n  Title: {title}"
            f"\n  Body: {body}"
            f"\n  Metadata: {metadata}"
        )
        return True
