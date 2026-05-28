import re
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy database models.
    Features:
    - Auto-generated snake_case table names based on class names.
    - Standard UUIDv4 primary key.
    - Standard timezone-aware created_at and updated_at timestamps.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Generate __tablename__ automatically in snake_case
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case, e.g., DeviceSession -> device_sessions
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        if name.endswith("y"):
            return f"{name[:-1]}ies"
        elif name.endswith("s"):
            return name
        return f"{name}s"
