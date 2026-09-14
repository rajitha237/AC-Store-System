from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)
from app.services.sms_notifications import (
    list_sms_notifications,
)


def field(value, name):
    if isinstance(value, dict):
        return value[name]

    return getattr(
        value,
        name,
    )


@pytest.mark.asyncio
async def test_sms_center_masks_phone_and_returns_summary(
    db_session,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    now_utc = datetime.now(
        timezone.utc
    )

    sent_row = SmsNotification(
        company_id=company.id,
        job_card_id=None,
        customer_id=None,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone=(
            "+94771234567"
        ),
        event_type=(
            "owner_daily_cash_summary"
        ),
        message=(
            "Daily summary test message"
        ),
        status=(
            SmsNotificationStatus.SENT.value
        ),
        deduplication_key=(
            "test-sms-center-sent-1"
        ),
        provider_message_id=(
            "provider-test-1"
        ),
        attempt_count=1,
        sent_at=now_utc,
    )

    failed_row = SmsNotification(
        company_id=company.id,
        job_card_id=None,
        customer_id=None,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone=(
            "+94779876543"
        ),
        event_type=(
            "owner_job_visit_reminder"
        ),
        message=(
            "Failed reminder test"
        ),
        status=(
            SmsNotificationStatus.FAILED.value
        ),
        deduplication_key=(
            "test-sms-center-failed-1"
        ),
        provider_message_id=None,
        attempt_count=1,
        last_error=(
            "provider unavailable"
        ),
    )

    db_session.add_all(
        [
            sent_row,
            failed_row,
        ]
    )

    await db_session.commit()

    result = (
        await list_sms_notifications(
            db_session,
            company_id=company.id,
            timezone_name=(
                company.timezone
                or "Asia/Colombo"
            ),
            page=1,
            page_size=20,
        )
    )

    assert field(result, "total") >= 2

    assert (
        field(field(result, "summary"), "sent")
        >= 1
    )

    assert (
        field(field(result, "summary"), "failed")
        >= 1
    )

    assert (
        field(field(result, "summary"), "today_sent")
        >= 1
    )

    matching = [
        item
        for item in field(result, "items")
        if (
            field(item, "event_type")
            == "owner_daily_cash_summary"
        )
    ]

    assert matching

    item = matching[0]

    assert (
        field(item, "recipient_phone")
        != "+94771234567"
    )

    assert "*" in (
        field(item, "recipient_phone")
    )

    assert (
        field(item, "status")
        == SmsNotificationStatus.SENT.value
    )


@pytest.mark.asyncio
async def test_sms_center_filters_event_status_and_search(
    db_session,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    row = SmsNotification(
        company_id=company.id,
        job_card_id=None,
        customer_id=None,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone=(
            "+94771234567"
        ),
        event_type=(
            "owner_daily_cash_summary"
        ),
        message=(
            "Unique Daily Summary ABC987"
        ),
        status=(
            SmsNotificationStatus.PENDING.value
        ),
        deduplication_key=(
            "test-sms-center-filter-1"
        ),
        provider_message_id=None,
        attempt_count=0,
    )

    db_session.add(
        row
    )

    await db_session.commit()

    result = (
        await list_sms_notifications(
            db_session,
            company_id=company.id,
            timezone_name=(
                company.timezone
                or "Asia/Colombo"
            ),
            page=1,
            page_size=20,
            search="ABC987",
            status=(
                SmsNotificationStatus.PENDING.value
            ),
            recipient_type=(
                SmsRecipientType.OWNER.value
            ),
            event_type=(
                "owner_daily_cash_summary"
            ),
        )
    )

    assert field(result, "total") == 1
    assert len(field(result, "items")) == 1

    item = field(result, "items")[0]

    assert (
        field(item, "event_type")
        == "owner_daily_cash_summary"
    )

    assert (
        field(item, "status")
        == SmsNotificationStatus.PENDING.value
    )

    assert (
        field(item, "recipient_type")
        == SmsRecipientType.OWNER.value
    )


@pytest.mark.asyncio
async def test_sms_center_pagination(
    db_session,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    for index in range(3):
        db_session.add(
            SmsNotification(
                company_id=company.id,
                job_card_id=None,
                customer_id=None,
                recipient_type=(
                    SmsRecipientType.OWNER.value
                ),
                recipient_phone=(
                    "+94771234567"
                ),
                event_type=(
                    "pagination_test"
                ),
                message=(
                    f"Pagination {index}"
                ),
                status=(
                    SmsNotificationStatus.PENDING.value
                ),
                deduplication_key=(
                    "test-sms-center-page-"
                    f"{index}"
                ),
                provider_message_id=None,
                attempt_count=0,
            )
        )

    await db_session.commit()

    result = (
        await list_sms_notifications(
            db_session,
            company_id=company.id,
            timezone_name=(
                company.timezone
                or "Asia/Colombo"
            ),
            page=1,
            page_size=2,
            event_type=(
                "pagination_test"
            ),
        )
    )

    assert field(result, "total") == 3
    assert len(field(result, "items")) == 2
    assert field(result, "page") == 1
    assert field(result, "page_size") == 2
    assert field(result, "total_pages") == 2
