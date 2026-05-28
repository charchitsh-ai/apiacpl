from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNotificationProvider(ABC):
    """Abstract interface defining standard dispatch operations for communication channels."""

    @abstractmethod
    async def send(self, to: str, title: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Dispatches a message payload.
        Returns True on success, False/raises exception on failure.
        """
        pass
