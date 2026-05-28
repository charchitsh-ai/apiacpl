from app.services.providers.base import BaseNotificationProvider
from app.services.providers.whatsapp import WhatsAppProvider
from app.services.providers.sms import SMSProvider
from app.services.providers.email import EmailProvider
from app.services.providers.push import PushProvider


# Singleton provider instances (initialized once at module load)
_providers: dict[str, BaseNotificationProvider] = {
    "whatsapp": WhatsAppProvider(),
    "sms": SMSProvider(),
    "email": EmailProvider(),
    "push": PushProvider(),
}


def get_provider(channel: str) -> BaseNotificationProvider:
    """
    Factory function resolving the appropriate notification provider by channel name.
    Raises ValueError for unknown channels.
    """
    provider = _providers.get(channel.lower())
    if not provider:
        raise ValueError(
            f"Unsupported notification channel '{channel}'. "
            f"Valid channels: {list(_providers.keys())}"
        )
    return provider
