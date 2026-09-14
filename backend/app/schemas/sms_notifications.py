from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SmsNotificationSummaryResponse(BaseModel):
    total: int
    sent: int
    pending: int
    processing: int
    failed: int
    cancelled: int
    today_sent: int


class SmsNotificationResponse(BaseModel):
    id: int

    recipient_type: str
    recipient_name: str | None = None
    recipient_phone: str

    event_type: str

    job_card_id: int | None = None
    job_number: str | None = None

    customer_id: int | None = None
    customer_number: str | None = None

    message: str
    status: str

    attempt_count: int
    provider_message_id: str | None = None
    last_error: str | None = None

    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime


class SmsNotificationListResponse(BaseModel):
    items: list[SmsNotificationResponse]

    total: int
    page: int
    page_size: int
    total_pages: int

    summary: SmsNotificationSummaryResponse
