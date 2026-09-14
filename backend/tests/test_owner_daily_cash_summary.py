from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)
from app.services.sms import (
    OWNER_DAILY_CASH_SUMMARY_EVENT,
    build_owner_daily_cash_summary_key,
    build_owner_daily_cash_summary_message,
    queue_owner_daily_cash_summary,
)


def test_daily_cash_summary_helpers():
    summary_date = date(
        2026,
        9,
        14,
    )

    key = (
        build_owner_daily_cash_summary_key(
            company_id=1,
            summary_date=summary_date,
        )
    )

    assert key == (
        "owner-daily-cash-summary:"
        "1:2026-09-14"
    )

    message = (
        build_owner_daily_cash_summary_message(
            summary_date=summary_date,
            total_cash_in=Decimal(
                "125000.00"
            ),
            total_cash_out=Decimal(
                "35000.00"
            ),
            net_cash_flow=Decimal(
                "90000.00"
            ),
        )
    )

    assert (
        "2026-09-14"
        in message
    )

    assert (
        "Income LKR 125,000.00"
        in message
    )

    assert (
        "Expenses LKR 35,000.00"
        in message
    )

    assert (
        "Net LKR 90,000.00"
        in message
    )


@pytest.mark.asyncio
async def test_daily_cash_summary_before_9pm_does_not_queue(
    db_session,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    local_now = datetime(
        2026,
        9,
        14,
        20,
        59,
        tzinfo=ZoneInfo(
            "Asia/Colombo"
        ),
    )

    rows = (
        await queue_owner_daily_cash_summary(
            db_session,
            company_id=company.id,
            local_now=local_now,
            timezone_name="Asia/Colombo",
        )
    )

    assert rows == []


@pytest.mark.asyncio
async def test_daily_cash_summary_queues_once_after_9pm(
    db_session,
    monkeypatch,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    company.owner_sms_phone = (
        "0771234567"
    )

    await db_session.commit()

    async def fake_report(
        session,
        *,
        company_id,
        date_from,
        date_to,
        timezone_name,
    ):
        assert session is db_session
        assert company_id == company.id

        assert (
            date_from
            == date(
                2026,
                9,
                14,
            )
        )

        assert date_to == date_from

        assert (
            timezone_name
            == "Asia/Colombo"
        )

        return SimpleNamespace(
            cash_flow=SimpleNamespace(
                total_cash_in=Decimal(
                    "125000.00"
                ),
                total_cash_out=Decimal(
                    "35000.00"
                ),
                net_cash_flow=Decimal(
                    "90000.00"
                ),
            )
        )

    monkeypatch.setattr(
        "app.services.reports."
        "build_financial_reports_summary",
        fake_report,
    )

    local_now = datetime(
        2026,
        9,
        14,
        21,
        0,
        tzinfo=ZoneInfo(
            "Asia/Colombo"
        ),
    )

    first = (
        await queue_owner_daily_cash_summary(
            db_session,
            company_id=company.id,
            local_now=local_now,
            timezone_name="Asia/Colombo",
        )
    )

    assert len(first) == 1

    row = first[0]

    assert (
        row.event_type
        == OWNER_DAILY_CASH_SUMMARY_EVENT
    )

    assert (
        row.recipient_type
        == SmsRecipientType.OWNER.value
    )

    assert (
        row.recipient_phone
        == "+94771234567"
    )

    assert (
        row.status
        == SmsNotificationStatus.PENDING.value
    )

    assert row.job_card_id is None
    assert row.customer_id is None
    assert row.attempt_count == 0

    assert (
        "Income LKR 125,000.00"
        in row.message
    )

    assert (
        "Expenses LKR 35,000.00"
        in row.message
    )

    assert (
        "Net LKR 90,000.00"
        in row.message
    )

    await db_session.commit()

    second = (
        await queue_owner_daily_cash_summary(
            db_session,
            company_id=company.id,
            local_now=local_now,
            timezone_name="Asia/Colombo",
        )
    )

    assert second == []

    rows = (
        await db_session.execute(
            select(
                SmsNotification
            ).where(
                SmsNotification.company_id
                == company.id,
                SmsNotification.event_type
                == OWNER_DAILY_CASH_SUMMARY_EVENT,
            )
        )
    ).scalars().all()

    assert len(rows) == 1

    assert (
        rows[0].deduplication_key
        == (
            "owner-daily-cash-summary:"
            f"{company.id}:"
            "2026-09-14"
        )
    )


@pytest.mark.asyncio
async def test_daily_cash_summary_requires_owner_phone(
    db_session,
):
    company = (
        await db_session.execute(
            select(Company)
            .order_by(Company.id)
        )
    ).scalars().first()

    assert company is not None

    company.owner_sms_phone = None

    await db_session.commit()

    local_now = datetime(
        2026,
        9,
        14,
        21,
        0,
        tzinfo=ZoneInfo(
            "Asia/Colombo"
        ),
    )

    rows = (
        await queue_owner_daily_cash_summary(
            db_session,
            company_id=company.id,
            local_now=local_now,
            timezone_name="Asia/Colombo",
        )
    )

    assert rows == []
