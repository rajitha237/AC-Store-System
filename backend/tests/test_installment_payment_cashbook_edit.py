from datetime import date, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    Customer,
    CustomerPayment,
    InstallmentPaymentAllocation,
    InstallmentPlan,
    InstallmentSchedule,
)
from tests.test_installments_customer_ledger import (
    create_confirmed_invoice,
    create_plan,
    dec,
)


async def create_two_installment_payments(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
):
    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
    )

    invoice = fixture["confirmed"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
    )

    first_response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount": "600.00",
            "payment_method": "cash",
            "reference_number":
                f"FIRST-{suffix}",
            "notes":
                "First installment payment",
        },
    )

    assert first_response.status_code == 201, (
        first_response.text
    )

    second_response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount": "400.00",
            "payment_method": "cash",
            "reference_number":
                f"SECOND-{suffix}",
            "notes":
                "Later installment payment",
        },
    )

    assert second_response.status_code == 201, (
        second_response.text
    )

    return {
        "fixture": fixture,
        "plan": plan,
        "first": first_response.json(),
        "second": second_response.json(),
    }


async def accounting_snapshot(
    db_session,
    *,
    plan_id,
    customer_id,
):
    db_session.expire_all()

    plan = await db_session.get(
        InstallmentPlan,
        plan_id,
    )

    customer = await db_session.get(
        Customer,
        customer_id,
    )

    schedules_result = await db_session.execute(
        select(InstallmentSchedule)
        .where(
            InstallmentSchedule.plan_id
            == plan_id
        )
        .order_by(
            InstallmentSchedule.installment_number
        )
    )

    allocations_result = await db_session.execute(
        select(InstallmentPaymentAllocation)
        .where(
            InstallmentPaymentAllocation.plan_id
            == plan_id
        )
        .order_by(
            InstallmentPaymentAllocation.id
        )
    )

    assert plan is not None
    assert customer is not None

    schedules = (
        schedules_result.scalars().all()
    )

    allocations = (
        allocations_result.scalars().all()
    )

    return {
        "plan_total_paid":
            dec(plan.total_paid),
        "plan_outstanding":
            dec(plan.outstanding_amount),
        "plan_status":
            plan.status,
        "customer_balance":
            dec(customer.current_balance),
        "schedules": [
            (
                row.id,
                dec(row.amount_paid),
                row.status,
            )
            for row in schedules
        ],
        "allocations": [
            (
                row.id,
                row.payment_id,
                row.schedule_id,
                dec(row.amount),
                dec(row.principal_amount),
                dec(row.interest_amount),
                row.is_reversed,
            )
            for row in allocations
        ],
    }


@pytest.mark.asyncio
async def test_installment_payment_metadata_edit_preserves_accounting(
    client,
    admin_headers,
    db_session,
):
    data = await create_two_installment_payments(
        client,
        admin_headers,
        db_session,
        suffix="901",
    )

    plan = data["plan"]
    first = data["first"]
    fixture = data["fixture"]

    customer_id = fixture["customer"]["id"]
    payment_id = first["payment_id"]

    before = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    payment_before = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_before is not None

    original_amount = dec(
        payment_before.amount
    )

    edit_date = date.today() - timedelta(
        days=2
    )

    response = await client.patch(
        f"/api/v1/payments/{payment_id}",
        headers=admin_headers,
        json={
            "payment_date":
                edit_date.isoformat(),
            "amount":
                str(original_amount),
            "payment_method":
                "bank_transfer",
            "reference_number":
                "CB-EDIT-901",
            "notes":
                "Cash Book metadata correction",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    body = response.json()

    assert (
        body["installment_plan_id"]
        == plan["id"]
    )

    db_session.expire_all()

    payment_after = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_after is not None

    assert dec(
        payment_after.amount
    ) == original_amount

    assert (
        payment_after.payment_method
        == "bank_transfer"
    )

    assert (
        payment_after.reference_number
        == "CB-EDIT-901"
    )

    assert (
        payment_after.notes
        == "Cash Book metadata correction"
    )

    stored_payment_date = (
        payment_after.payment_date
    )

    assert stored_payment_date is not None

    if stored_payment_date.tzinfo is None:
        stored_payment_date = (
            stored_payment_date.replace(
                tzinfo=timezone.utc
            )
        )

    local_payment_date = (
        stored_payment_date
        .astimezone(
            ZoneInfo("Asia/Colombo")
        )
        .date()
    )

    assert local_payment_date == edit_date

    after = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    assert after == before


@pytest.mark.asyncio
async def test_historical_installment_amount_edit_is_blocked_atomically(
    client,
    admin_headers,
    db_session,
):
    data = await create_two_installment_payments(
        client,
        admin_headers,
        db_session,
        suffix="902",
    )

    plan = data["plan"]
    first = data["first"]
    fixture = data["fixture"]

    customer_id = fixture["customer"]["id"]
    payment_id = first["payment_id"]

    before = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    payment_before = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_before is not None

    payment_snapshot = (
        dec(payment_before.amount),
        payment_before.payment_method,
        payment_before.reference_number,
        payment_before.notes,
        payment_before.payment_date,
    )

    response = await client.patch(
        f"/api/v1/payments/{payment_id}",
        headers=admin_headers,
        json={
            "payment_date":
                date.today().isoformat(),
            "amount": "650.00",
            "payment_method":
                "bank_transfer",
            "reference_number":
                "MUST-NOT-SAVE",
            "notes":
                "Must be rejected",
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    assert (
        "historical installment payment"
        in response.json()["detail"].lower()
    )

    db_session.expire_all()

    payment_after = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_after is not None

    assert (
        dec(payment_after.amount),
        payment_after.payment_method,
        payment_after.reference_number,
        payment_after.notes,
        payment_after.payment_date,
    ) == payment_snapshot

    after = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    assert after == before


@pytest.mark.asyncio
async def test_installment_payment_future_date_is_rejected_atomically(
    client,
    admin_headers,
    db_session,
):
    data = await create_two_installment_payments(
        client,
        admin_headers,
        db_session,
        suffix="903",
    )

    plan = data["plan"]
    first = data["first"]
    fixture = data["fixture"]

    customer_id = fixture["customer"]["id"]
    payment_id = first["payment_id"]

    payment_before = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_before is not None

    amount = dec(
        payment_before.amount
    )

    before = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    response = await client.patch(
        f"/api/v1/payments/{payment_id}",
        headers=admin_headers,
        json={
            "payment_date": (
                date.today()
                + timedelta(days=1)
            ).isoformat(),
            "amount": str(amount),
            "payment_method": "cash",
            "reference_number":
                "FUTURE-MUST-NOT-SAVE",
            "notes":
                "Future date rejection",
        },
    )

    assert response.status_code == 422, (
        response.text
    )

    assert (
        "future"
        in response.json()["detail"].lower()
    )

    after = await accounting_snapshot(
        db_session,
        plan_id=plan["id"],
        customer_id=customer_id,
    )

    assert after == before
