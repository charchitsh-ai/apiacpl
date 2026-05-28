from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class NotificationTemplateBase(BaseModel):
    name: str = Field(..., description="Unique template identifier name")
    type: str = Field(..., description="Template notification type")
    subject: Optional[str] = Field(None, description="Email subject line if applicable")
    body: str = Field(..., description="Message template with placeholders")
    variables: List[str] = Field(default_factory=list, description="Placeholders list")
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateResponse(NotificationTemplateBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    user_id: uuid.UUID
    type: str
    title: str
    message: str
    channel: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(NotificationBase):
    id: uuid.UUID
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationPaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[NotificationResponse]


# Dispatch Request Schemas
class WhatsAppNotificationRequest(BaseModel):
    phone: str = Field(..., description="Mobile number with country code")
    template_name: str = Field(..., description="Template name to render")
    variables: Dict[str, str] = Field(default_factory=dict, description="Key-value mapping variables")


class SMSNotificationRequest(BaseModel):
    phone: str = Field(..., description="Mobile number")
    message: str = Field(..., min_length=1, max_length=160, description="SMS content body")


class EmailNotificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject line")
    body: str = Field(..., min_length=1, description="HTML or plain text body")


class PushNotificationRequest(BaseModel):
    user_id: uuid.UUID = Field(..., description="Target User ID")
    title: str = Field(..., min_length=1, description="Push alert title")
    body: str = Field(..., min_length=1, description="Push alert content")


class AppointmentReminderRequest(BaseModel):
    appointment_id: uuid.UUID = Field(..., description="Target Appointment ID")
    reminder_type: str = Field(..., description="Type: 24h_before, 2h_before")
    scheduled_at: datetime = Field(..., description="Datetime schedule timestamp")


class FollowUpReminderRequest(BaseModel):
    appointment_id: uuid.UUID = Field(..., description="Target Appointment ID")
    scheduled_at: datetime = Field(..., description="Datetime schedule timestamp")
