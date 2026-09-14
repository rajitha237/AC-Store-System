from __future__ import annotations

from datetime import (
    datetime,
    time,
    timezone,
)
from math import ceil
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    case,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.service import ServiceJobCard
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
)


def _mask_phone(
    phone: str,
) -> str:
    value = phone.strip()

    if len(value) <= 4:
        return "*" * len(value)

    if len(value) <= 7:
        return (
            value[:2]
            + ("*" * (len(value) - 4))
            + value[-2:]
        )

    return (
        value[:3]
        + ("*" * (len(value) - 5))
        + value[-2:]
    )


def _local_day_bounds_utc(
    *,
    now_utc: datetime,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    try:
        local_tz = ZoneInfo(
            timezone_name
        )
    except Exception:
        local_tz = timezone.utc

    local_now = now_utc.astimezone(
        local_tz
    )

    local_start = datetime.combine(
        local_now.date(),
        time.min,
        tzinfo=local_tz,
    )

    local_end = datetime.combine(
        local_now.date(),
        time.max,
        tzinfo=local_tz,
    )

    return (
        local_start.astimezone(
            timezone.utc
        ),
        local_end.astimezone(
            timezone.utc
        ),
    )


async def list_sms_notifications(
    session: AsyncSession,
    *,
    company_id: int,
    timezone_name: str,
    page: int,
    page_size: int,
    search: str | None = None,
    status: str | None = None,
    recipient_type: str | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    filters = [
        SmsNotification.company_id
        == company_id
    ]

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                SmsNotification.message.ilike(
                    pattern
                ),
                SmsNotification.recipient_phone.ilike(
                    pattern
                ),
                SmsNotification.event_type.ilike(
                    pattern
                ),
                Customer.full_name.ilike(
                    pattern
                ),
                Customer.customer_number.ilike(
                    pattern
                ),
                ServiceJobCard.job_number.ilike(
                    pattern
                ),
            )
        )

    if status and status.strip():
        filters.append(
            SmsNotification.status
            == status.strip()
        )

    if (
        recipient_type
        and recipient_type.strip()
    ):
        filters.append(
            SmsNotification.recipient_type
            == recipient_type.strip()
        )

    if event_type and event_type.strip():
        filters.append(
            SmsNotification.event_type
            == event_type.strip()
        )

    if date_from is not None:
        filters.append(
            SmsNotification.created_at
            >= date_from
        )

    if date_to is not None:
        filters.append(
            SmsNotification.created_at
            <= date_to
        )

    base_join = (
        select(SmsNotification)
        .outerjoin(
            Customer,
            Customer.id
            == SmsNotification.customer_id,
        )
        .outerjoin(
            ServiceJobCard,
            ServiceJobCard.id
            == SmsNotification.job_card_id,
        )
    )

    total = int(
        await session.scalar(
            select(
                func.count()
            )
            .select_from(
                SmsNotification
            )
            .outerjoin(
                Customer,
                Customer.id
                == SmsNotification.customer_id,
            )
            .outerjoin(
                ServiceJobCard,
                ServiceJobCard.id
                == SmsNotification.job_card_id,
            )
            .where(
                *filters
            )
        )
        or 0
    )

    result = await session.execute(
        select(
            SmsNotification,
            Customer.full_name,
            Customer.customer_number,
            ServiceJobCard.job_number,
        )
        .outerjoin(
            Customer,
            Customer.id
            == SmsNotification.customer_id,
        )
        .outerjoin(
            ServiceJobCard,
            ServiceJobCard.id
            == SmsNotification.job_card_id,
        )
        .where(
            *filters
        )
        .order_by(
            SmsNotification.created_at.desc(),
            SmsNotification.id.desc(),
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(
            page_size
        )
    )

    items: list[dict[str, Any]] = []

    for (
        notification,
        customer_name,
        customer_number,
        job_number,
    ) in result.all():
        recipient_name = (
            customer_name
            if (
                notification.recipient_type
                == "customer"
            )
            else "Owner"
        )

        items.append(
            {
                "id":
                    notification.id,
                "recipient_type":
                    notification.recipient_type,
                "recipient_name":
                    recipient_name,
                "recipient_phone":
                    _mask_phone(
                        notification.recipient_phone
                    ),
                "event_type":
                    notification.event_type,
                "job_card_id":
                    notification.job_card_id,
                "job_number":
                    job_number,
                "customer_id":
                    notification.customer_id,
                "customer_number":
                    customer_number,
                "message":
                    notification.message,
                "status":
                    notification.status,
                "attempt_count":
                    notification.attempt_count,
                "provider_message_id":
                    notification.provider_message_id,
                "last_error":
                    notification.last_error,
                "scheduled_for":
                    notification.scheduled_for,
                "sent_at":
                    notification.sent_at,
                "created_at":
                    notification.created_at,
            }
        )

    now_utc = datetime.now(
        timezone.utc
    )

    (
        today_start,
        today_end,
    ) = _local_day_bounds_utc(
        now_utc=now_utc,
        timezone_name=timezone_name,
    )

    summary_row = (
        await session.execute(
            select(
                func.count(
                    SmsNotification.id
                ).label(
                    "total"
                ),
                func.sum(
                    case(
                        (
                            SmsNotification.status
                            == SmsNotificationStatus.SENT.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "sent"
                ),
                func.sum(
                    case(
                        (
                            SmsNotification.status
                            == SmsNotificationStatus.PENDING.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "pending"
                ),
                func.sum(
                    case(
                        (
                            SmsNotification.status
                            == SmsNotificationStatus.PROCESSING.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "processing"
                ),
                func.sum(
                    case(
                        (
                            SmsNotification.status
                            == SmsNotificationStatus.FAILED.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "failed"
                ),
                func.sum(
                    case(
                        (
                            SmsNotification.status
                            == SmsNotificationStatus.CANCELLED.value,
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "cancelled"
                ),
                func.sum(
                    case(
                        (
                            (
                                SmsNotification.status
                                == SmsNotificationStatus.SENT.value
                            )
                            & (
                                SmsNotification.sent_at
                                >= today_start
                            )
                            & (
                                SmsNotification.sent_at
                                <= today_end
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label(
                    "today_sent"
                ),
            )
            .where(
                SmsNotification.company_id
                == company_id
            )
        )
    ).one()

    summary = {
        "total":
            int(
                summary_row.total
                or 0
            ),
        "sent":
            int(
                summary_row.sent
                or 0
            ),
        "pending":
            int(
                summary_row.pending
                or 0
            ),
        "processing":
            int(
                summary_row.processing
                or 0
            ),
        "failed":
            int(
                summary_row.failed
                or 0
            ),
        "cancelled":
            int(
                summary_row.cancelled
                or 0
            ),
        "today_sent":
            int(
                summary_row.today_sent
                or 0
            ),
    }

    return {
        "items":
            items,
        "total":
            total,
        "page":
            page,
        "page_size":
            page_size,
        "total_pages":
            (
                ceil(
                    total
                    / page_size
                )
                if total
                else 0
            ),
        "summary":
            summary,
    }
