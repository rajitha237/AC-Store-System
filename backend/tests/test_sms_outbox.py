from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.installment import (
    InstallmentPlan,
    InstallmentPlanStatus,
    InstallmentSchedule,
    InstallmentScheduleStatus,
)
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)
from app.services.sms import (
    INSTALLMENT_DUE_REMINDER_EVENT,
    OWNER_JOB_REMINDER_EVENT,
    build_installment_due_reminder_key,
    build_installment_due_reminder_message,
    build_owner_job_reminder_key,
    build_owner_job_reminder_message,
    queue_installment_due_reminders,
    queue_owner_job_reminders,
)
from tests.test_installments_customer_ledger import (
    create_confirmed_invoice,
    create_plan,
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

    assert len(first) == 1

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

    assert len(rows) == 1

    assert {
        row.job_card_id
        for row in rows
    } == {
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

    assert len(final_rows) == 1


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




@pytest.mark.asyncio
async def test_installment_due_reminder_helpers():
    due_date = date(2026, 8, 15)

    key = build_installment_due_reminder_key(
        company_id=1,
        schedule_id=77,
        due_date=due_date,
    )

    assert key == (
        "installment-due-reminder:"
        "1:77:2026-08-15"
    )

    message = build_installment_due_reminder_message(
        agreement_number="INS-000077",
        due_date=due_date,
        remaining_amount=Decimal("1234.50"),
    )

    assert "INS-000077" in message
    assert "LKR 1234.50" in message
    assert "tomorrow" in message
    assert "2026-08-15" in message


@pytest.mark.asyncio
async def test_installment_due_reminder_full_and_dedupe(
    client,
    admin_headers,
    db_session,
):
    today = date(2026, 8, 14)
    due_date = today + timedelta(days=1)

    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix="951",
    )

    plan_data = await create_plan(
        client,
        admin_headers,
        fixture["confirmed"]["id"],
        count=4,
        first_due=due_date,
    )

    plan = (
        await db_session.execute(
            select(InstallmentPlan).where(
                InstallmentPlan.id
                == plan_data["id"]
            )
        )
    ).scalar_one()

    customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == plan.customer_id
            )
        )
    ).scalar_one()

    customer.sms_allowed = True
    customer.sms_phone = "0771234567"

    await db_session.commit()

    first = await queue_installment_due_reminders(
        db_session,
        company_id=plan.company_id,
        today=today,
    )

    await db_session.commit()

    assert len(first) == 1

    row = first[0]
    first_schedule = plan.schedules[0]

    expected_remaining = (
        Decimal(first_schedule.amount_due)
        - Decimal(first_schedule.amount_paid)
    )

    assert (
        row.event_type
        == INSTALLMENT_DUE_REMINDER_EVENT
    )
    assert (
        row.recipient_type
        == SmsRecipientType.CUSTOMER.value
    )
    assert row.recipient_phone == "+94771234567"
    assert plan.agreement_number in row.message
    assert (
        f"LKR {expected_remaining:.2f}"
        in row.message
    )
    assert "tomorrow" in row.message
    assert row.job_card_id is None
    assert row.customer_id == customer.id
    assert (
        row.status
        == SmsNotificationStatus.PENDING.value
    )

    second = await queue_installment_due_reminders(
        db_session,
        company_id=plan.company_id,
        today=today,
    )

    await db_session.commit()

    assert second == []

    rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.event_type
                == INSTALLMENT_DUE_REMINDER_EVENT,
                SmsNotification.customer_id
                == customer.id,
            )
        )
    ).scalars().all()

    assert len(rows) == 1


@pytest.mark.asyncio
async def test_installment_partial_reminder_uses_remaining(
    client,
    admin_headers,
    db_session,
):
    today = date(2026, 8, 14)
    due_date = today + timedelta(days=1)

    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix="952",
    )

    plan_data = await create_plan(
        client,
        admin_headers,
        fixture["confirmed"]["id"],
        count=4,
        first_due=due_date,
    )

    plan = (
        await db_session.execute(
            select(InstallmentPlan).where(
                InstallmentPlan.id
                == plan_data["id"]
            )
        )
    ).scalar_one()

    schedule = plan.schedules[0]
    customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == plan.customer_id
            )
        )
    ).scalar_one()

    customer.sms_allowed = True
    customer.sms_phone = "0771234567"

    schedule.amount_paid = Decimal("100.00")
    schedule.status = (
        InstallmentScheduleStatus.PARTIAL.value
    )

    await db_session.commit()

    queued = await queue_installment_due_reminders(
        db_session,
        company_id=plan.company_id,
        today=today,
    )

    await db_session.commit()

    assert len(queued) == 1

    expected_remaining = (
        Decimal(schedule.amount_due)
        - Decimal("100.00")
    )

    assert (
        f"LKR {expected_remaining:.2f}"
        in queued[0].message
    )


@pytest.mark.asyncio
async def test_installment_reminder_skips_ineligible_rows(
    client,
    admin_headers,
    db_session,
):
    today = date(2026, 8, 14)
    due_date = today + timedelta(days=1)

    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix="953",
    )

    plan_data = await create_plan(
        client,
        admin_headers,
        fixture["confirmed"]["id"],
        count=4,
        first_due=due_date,
    )

    plan = (
        await db_session.execute(
            select(InstallmentPlan).where(
                InstallmentPlan.id
                == plan_data["id"]
            )
        )
    ).scalar_one()

    customer = (
        await db_session.execute(
            select(Customer).where(
                Customer.id == plan.customer_id
            )
        )
    ).scalar_one()
    customer.sms_allowed = False
    customer.sms_phone = "0771234567"

    await db_session.commit()

    no_consent = (
        await queue_installment_due_reminders(
            db_session,
            company_id=plan.company_id,
            today=today,
        )
    )

    assert no_consent == []

    customer.sms_allowed = True
    customer.sms_phone = "invalid-number"

    await db_session.commit()

    invalid_phone = (
        await queue_installment_due_reminders(
            db_session,
            company_id=plan.company_id,
            today=today,
        )
    )

    assert invalid_phone == []

    customer.sms_phone = "0771234567"
    plan.status = (
        InstallmentPlanStatus.COMPLETED.value
    )

    await db_session.commit()

    inactive = await queue_installment_due_reminders(
        db_session,
        company_id=plan.company_id,
        today=today,
    )

    assert inactive == []

    plan.status = InstallmentPlanStatus.ACTIVE.value

    schedule = plan.schedules[0]
    schedule.amount_paid = schedule.amount_due
    schedule.status = (
        InstallmentScheduleStatus.PAID.value
    )

    await db_session.commit()

    paid = await queue_installment_due_reminders(
        db_session,
        company_id=plan.company_id,
        today=today,
    )

    assert paid == []


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

    created_job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="919",
    )

    job = (
        await db_session.execute(
            select(ServiceJobCard).where(
                ServiceJobCard.id == created_job["id"]
            )
        )
    ).scalar_one()

    # Creation must queue exactly one "received" SMS.
    received_rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.job_card_id == job.id,
                SmsNotification.event_type
                == "customer_service_received",
            )
        )
    ).scalars().all()

    assert len(received_rows) == 1
    assert job.job_number in received_rows[0].message

    # READY requires a completed testing result.
    job.testing_result = "SMS workflow test passed"
    await db_session.commit()

    # Drive the normal workflow to READY.
    transitions = (
        "inspection",
        "waiting_approval",
        "approved",
        "repairing",
        "testing",
        "ready",
    )

    for new_status in transitions:
        response = await client.post(
            f"/api/v1/service/jobs/{job.id}/status",
            headers=admin_headers,
            json={
                "new_status": new_status,
                "remarks": f"Move to {new_status}",
            },
        )

        assert response.status_code == 200, response.text

    ready_rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.job_card_id == job.id,
                SmsNotification.event_type
                == "customer_service_ready",
            )
        )
    ).scalars().all()

    assert len(ready_rows) == 1
    assert job.job_number in ready_rows[0].message
    assert "completed" in ready_rows[0].message.lower()

    # Intermediate statuses must not create customer SMS.
    intermediate_rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.job_card_id == job.id,
                SmsNotification.event_type.in_(
                    (
                        "customer_service_waiting_approval",
                        "customer_service_repairing",
                        "customer_service_delivered",
                    )
                ),
            )
        )
    ).scalars().all()

    assert intermediate_rows == []

    # Calling the same queue helper again must dedupe READY.
    duplicate = await queue_customer_service_status_notification(
        db_session,
        job=job,
        status_value="ready",
    )

    assert duplicate is None



@pytest.mark.asyncio
async def test_customer_sms_status_policy_exact():
    """
    Customer service SMS policy is intentionally limited to:

    received = service job placed/registered
    ready    = service work completed/ready
    """
    from app.services.sms import (
        CUSTOMER_SERVICE_STATUS_EVENTS,
        build_customer_service_status_message,
    )

    expected = {
        "received": "customer_service_received",
        "ready": "customer_service_ready",
    }

    assert CUSTOMER_SERVICE_STATUS_EVENTS == expected

    received_message = build_customer_service_status_message(
        job_number="JOB-000088",
        status_value="received",
    )
    assert "JOB-000088" in received_message
    assert "received" in received_message.lower()
    assert "registered" in received_message.lower()

    ready_message = build_customer_service_status_message(
        job_number="JOB-000088",
        status_value="ready",
    )
    assert "JOB-000088" in ready_message
    assert "completed" in ready_message.lower()
    assert "ready" in ready_message.lower()



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
        "inspection",
        "waiting_approval",
        "approved",
        "repairing",
        "testing",
        "delivered",
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

    # Job creation may already have queued the supported
    # customer_service_received notification. None of the
    # blocked statuses above may add another customer SMS.
    assert len(rows) == 1
    assert (
        rows[0].event_type
        == "customer_service_received"
    )

    await db_session.rollback()
