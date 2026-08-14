from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)
from app.services.sms import (
    OWNER_JOB_REMINDER_EVENT,
    build_owner_job_reminder_key,
    build_owner_job_reminder_message,
    queue_owner_job_reminders,
)
from tests.test_service import (
    create_customer,
    create_job,
)


@pytest.mark.asyncio
async def test_owner_reminder_helpers():
    today = date(2026, 8, 14)

    key = build_owner_job_reminder_key(
        company_id=1,
        job_card_id=99,
        visit_date=today,
    )

    assert key == (
        "owner-job-reminder:"
        "1:99:2026-08-14"
    )

    today_message = (
        build_owner_job_reminder_message(
            job_number="JOB-000099",
            visit_date=today,
            today=today,
        )
    )

    assert "JOB-000099" in today_message
    assert "today" in today_message

    tomorrow_message = (
        build_owner_job_reminder_message(
            job_number="JOB-000099",
            visit_date=(
                today + timedelta(days=1)
            ),
            today=today,
        )
    )

    assert "tomorrow" in tomorrow_message


@pytest.mark.asyncio
async def test_owner_job_reminders_queue_once_only(
    client,
    admin_headers,
    db_session,
):
    today = date(2026, 8, 14)

    customer = await create_customer(
        client,
        admin_headers,
        suffix="913",
    )

    today_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="913",
    )

    tomorrow_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="914",
    )

    outside_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="915",
    )

    for job_id, visit_date in (
        (
            today_job["id"],
            today,
        ),
        (
            tomorrow_job["id"],
            today + timedelta(days=1),
        ),
        (
            outside_job["id"],
            today + timedelta(days=2),
        ),
    ):
        response = await client.patch(
            f"/api/v1/service/jobs/{job_id}",
            headers=admin_headers,
            json={
                "scheduled_visit_date":
                    visit_date.isoformat(),
            },
        )

        assert response.status_code == 200, (
            response.text
        )

    company = (
        await db_session.execute(
            select(Company).where(
                Company.id
                == today_job["company_id"]
            )
        )
    ).scalar_one()

    company.owner_sms_phone = (
        "0771234567"
    )

    # Commit setup because API requests and this fixture
    # use separate sessions.
    await db_session.commit()

    first = await queue_owner_job_reminders(
        db_session,
        company_id=company.id,
        today=today,
    )

    await db_session.commit()

    assert len(first) == 2

    rows = (
        await db_session.execute(
            select(SmsNotification)
            .where(
                SmsNotification.company_id
                == company.id,
                SmsNotification.event_type
                == OWNER_JOB_REMINDER_EVENT,
            )
            .order_by(
                SmsNotification.job_card_id
            )
        )
    ).scalars().all()

    assert len(rows) == 2

    assert {
        row.job_card_id
        for row in rows
    } == {
        today_job["id"],
        tomorrow_job["id"],
    }

    for row in rows:
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

        assert row.attempt_count == 0
        assert row.sent_at is None

        assert (
            row.job_card_id
            is not None
        )

        assert (
            row.deduplication_key
        )

    second = await queue_owner_job_reminders(
        db_session,
        company_id=company.id,
        today=today,
    )

    await db_session.commit()

    assert second == []

    final_rows = (
        await db_session.execute(
            select(SmsNotification)
            .where(
                SmsNotification.company_id
                == company.id,
                SmsNotification.event_type
                == OWNER_JOB_REMINDER_EVENT,
            )
        )
    ).scalars().all()

    assert len(final_rows) == 2


@pytest.mark.asyncio
async def test_owner_job_reminder_requires_owner_phone(
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

    queued = await queue_owner_job_reminders(
        db_session,
        company_id=company.id,
        today=date(2026, 8, 14),
    )

    assert queued == []


from app.models.customer import Customer
from app.models.service import ServiceJobCard
from app.services.sms import (
    CUSTOMER_SERVICE_STATUS_EVENTS,
    build_customer_service_status_key,
    build_customer_service_status_message,
    queue_customer_service_status_notification,
)


@pytest.mark.asyncio
async def test_customer_service_status_helpers():
    key = build_customer_service_status_key(
        company_id=1,
        job_card_id=88,
        status_value="ready",
    )

    assert key == (
        "customer-service-status:"
        "1:88:ready"
    )

    message = (
        build_customer_service_status_message(
            job_number="JOB-000088",
            status_value="ready",
        )
    )

    assert "JOB-000088" in message
    assert "ready" in message.lower()

    assert (
        CUSTOMER_SERVICE_STATUS_EVENTS["ready"]
        == "customer_service_ready"
    )


@pytest.mark.asyncio
async def test_customer_service_status_queue_once_only(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="916",
    )

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="916",
    )

    db_customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == customer["id"]
            )
        )
    ).scalar_one()

    db_customer.sms_allowed = True
    db_customer.sms_phone = "0771234567"

    await db_session.commit()

    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id
                == created_job["id"]
            )
        )
    ).scalar_one()

    first = (
        await queue_customer_service_status_notification(
            db_session,
            job=job,
            status_value="ready",
        )
    )

    await db_session.commit()

    assert first is not None

    row = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.id == first.id
            )
        )
    ).scalar_one()

    assert (
        row.recipient_type
        == SmsRecipientType.CUSTOMER.value
    )

    assert row.recipient_phone == "+94771234567"

    assert (
        row.event_type
        == "customer_service_ready"
    )

    assert (
        row.status
        == SmsNotificationStatus.PENDING.value
    )

    assert row.attempt_count == 0
    assert row.sent_at is None

    second = (
        await queue_customer_service_status_notification(
            db_session,
            job=job,
            status_value="ready",
        )
    )

    await db_session.commit()

    assert second is None

    count = len(
        (
            await db_session.execute(
                select(SmsNotification).where(
                    SmsNotification.job_card_id
                    == job.id,
                    SmsNotification.event_type
                    == "customer_service_ready",
                )
            )
        ).scalars().all()
    )

    assert count == 1


@pytest.mark.asyncio
async def test_customer_service_sms_respects_consent(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="917",
    )

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="917",
    )

    db_customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == customer["id"]
            )
        )
    ).scalar_one()

    db_customer.sms_allowed = False

    await db_session.commit()

    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id
                == created_job["id"]
            )
        )
    ).scalar_one()

    queued = (
        await queue_customer_service_status_notification(
            db_session,
            job=job,
            status_value="ready",
        )
    )

    assert queued is None


@pytest.mark.asyncio
async def test_invalid_customer_sms_phone_does_not_fail_job_logic(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="918",
    )

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="918",
    )

    db_customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == customer["id"]
            )
        )
    ).scalar_one()

    db_customer.sms_allowed = True
    db_customer.sms_phone = "INVALID"

    await db_session.commit()

    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id
                == created_job["id"]
            )
        )
    ).scalar_one()

    queued = (
        await queue_customer_service_status_notification(
            db_session,
            job=job,
            status_value="ready",
        )
    )

    assert queued is None


@pytest.mark.asyncio
async def test_service_status_transition_queues_customer_sms_once(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="919",
    )

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="919",
    )

    db_customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == customer["id"]
            )
        )
    ).scalar_one()

    db_customer.sms_allowed = True
    db_customer.sms_phone = "0771234567"

    await db_session.commit()

    # received -> inspection
    response = await client.post(
        f"/api/v1/service/jobs/"
        f"{created_job['id']}/status",
        headers=admin_headers,
        json={
            "new_status": "inspection",
            "remarks": "Inspection started",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    # inspection -> waiting_approval
    response = await client.post(
        f"/api/v1/service/jobs/"
        f"{created_job['id']}/status",
        headers=admin_headers,
        json={
            "new_status": "waiting_approval",
            "remarks": "Approval required",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.job_card_id
                == created_job["id"],
                SmsNotification.event_type
                == (
                    "customer_service_"
                    "waiting_approval"
                ),
            )
        )
    ).scalars().all()

    assert len(rows) == 1

    row = rows[0]

    assert (
        row.status
        == SmsNotificationStatus.PENDING.value
    )

    assert (
        row.recipient_type
        == SmsRecipientType.CUSTOMER.value
    )

    assert row.recipient_phone == "+94771234567"

    assert created_job["job_number"] in row.message

    # Duplicate queue attempt must be blocked by
    # the same job/status deduplication key.
    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id
                == created_job["id"]
            )
        )
    ).scalar_one()

    duplicate = (
        await queue_customer_service_status_notification(
            db_session,
            job=job,
            status_value="waiting_approval",
        )
    )

    assert duplicate is None

    await db_session.rollback()


@pytest.mark.asyncio
async def test_customer_sms_status_policy_exact():
    """
    Only explicitly customer-relevant service statuses
    may generate customer SMS notifications.
    """
    from app.services.sms import (
        CUSTOMER_SERVICE_STATUS_EVENTS,
        build_customer_service_status_message,
    )

    expected = {
        "waiting_approval":
            "customer_service_waiting_approval",
        "repairing":
            "customer_service_repairing",
        "ready":
            "customer_service_ready",
        "delivered":
            "customer_service_delivered",
    }

    assert CUSTOMER_SERVICE_STATUS_EVENTS == expected

    for status_value in expected:
        message = build_customer_service_status_message(
            job_number="JOB-000999",
            status_value=status_value,
        )

        assert "JOB-000999" in message
        assert message.strip()

    blocked_statuses = {
        "received",
        "inspection",
        "approved",
        "testing",
        "cancelled",
    }

    assert (
        blocked_statuses
        & set(CUSTOMER_SERVICE_STATUS_EVENTS)
        == set()
    )


@pytest.mark.asyncio
async def test_unsupported_customer_status_does_not_queue_sms(
    client,
    admin_headers,
    db_session,
):
    """
    Internal/non-customer statuses must not create
    customer SMS outbox rows.
    """
    customer = await create_customer(
        client,
        admin_headers,
        suffix="920",
    )

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="920",
    )

    db_customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == customer["id"]
            )
        )
    ).scalar_one()

    db_customer.sms_allowed = True
    db_customer.sms_phone = "0771234567"

    await db_session.commit()

    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id
                == created_job["id"]
            )
        )
    ).scalar_one()

    blocked_statuses = (
        "received",
        "inspection",
        "approved",
        "testing",
        "cancelled",
    )

    for status_value in blocked_statuses:
        queued = (
            await queue_customer_service_status_notification(
                db_session,
                job=job,
                status_value=status_value,
            )
        )

        assert queued is None

    rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.job_card_id
                == job.id,
                SmsNotification.recipient_type
                == SmsRecipientType.CUSTOMER.value,
            )
        )
    ).scalars().all()

    assert rows == []

    await db_session.rollback()
