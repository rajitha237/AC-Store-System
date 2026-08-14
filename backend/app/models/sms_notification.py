from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


class SmsNotificationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SmsRecipientType(str, Enum):
    OWNER = "owner"
    CUSTOMER = "customer"


class SmsNotification(Base):
    __tablename__ = "sms_notifications"

    __table_args__ = (
        UniqueConstraint(
            "deduplication_key",
            name=(
                "uq_sms_notifications_"
                "deduplication_key"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    job_card_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    recipient_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    recipient_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=SmsNotificationStatus.PENDING.value,
        server_default=(
            SmsNotificationStatus.PENDING.value
        ),
        nullable=False,
        index=True,
    )

    deduplication_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    company: Mapped["Company"] = relationship()

    job_card: Mapped["ServiceJobCard | None"] = relationship()

    customer: Mapped["Customer | None"] = relationship()


from app.models.company import Company
from app.models.customer import Customer
from app.models.service import ServiceJobCard
