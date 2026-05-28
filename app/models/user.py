from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.token import RefreshToken
    from app.models.session import DeviceSession
    from app.models.doctor import Doctor


class User(Base):
    """User Model representing platform users (patients, doctors, or admins)."""

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    device_sessions: Mapped[List["DeviceSession"]] = relationship(
        "DeviceSession", back_populates="user", cascade="all, delete-orphan"
    )
    doctor_profile: Mapped["Doctor"] = relationship(
        "Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


