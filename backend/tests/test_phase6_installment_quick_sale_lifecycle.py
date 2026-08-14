"""
PHASE 6 - Installment + Quick Sale lifecycle regression.

IMPORTANT:
This module deliberately reuses the project's established
installment integration-test contract and pytest isolation.

It does NOT connect directly to production ac_store.db.

The purpose is to exercise the complete established installment
test surface as one Phase-6 regression module before a controlled
real UI transaction is attempted.
"""

# PHASE6_INSTALLMENT_QUICK_SALE_LIFECYCLE_V1

from datetime import (
    date,
    timedelta,
)
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    Customer,
    CustomerPayment,
    InstallmentPaymentAllocation,
    InstallmentPlan,
    InstallmentSchedule,
    SalesInvoice,
)
from tests.test_sales_payments import (
    confirm_invoice,
    create_sales_fixture,
    dec,
)


async def create_confirmed_invoice(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
    initial_payment=None,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice = fixture["invoice"]

    response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
        initial_payment=(
            initial_payment
        ),
    )

    assert response.status_code == 200, (
        response.text
    )

    return {
        **fixture,
        "confirmed":
            response.json(),
    }


async def create_plan(
    client,
    admin_headers,
    invoice_id,
    *,
    count=4,
    first_due=None,
):
    if first_due is None:
        first_due = (
            date.today()
            + timedelta(days=30)
        )

    response = await client.post(
        "/api/v1/installments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "first_due_date":
                first_due.isoformat(),
            "frequency":
                "monthly",
            "installment_count":
                count,
            "grace_days":
                3,
            "notes":
                "Installment test",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


@pytest.mark.asyncio
async def test_create_installment_plan_schedule(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="811",
            initial_payment={
                "amount":
                    "400.00",
                "payment_method":
                    "cash",
            },
        )
    )

    invoice = fixture["confirmed"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
    )

    assert plan["agreement_number"].startswith(
        "INS-"
    )

    assert plan["status"] == "active"

    assert dec(
        plan["financed_amount"]
    ) == Decimal("2000.00")

    assert len(
        plan["schedules"]
    ) == 4

    total = sum(
        (
            dec(item["amount_due"])
            for item
            in plan["schedules"]
        ),
        Decimal("0.00"),
    )

    assert total == Decimal(
        "2000.00"
    )


@pytest.mark.asyncio
async def test_installment_payment_fifo_and_receipt(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="812",
        )
    )

    invoice = fixture["confirmed"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
    )

    payment = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount":
                "700.00",
            "payment_method":
                "cash",
        },
    )

    assert payment.status_code == 201, (
        payment.text
    )

    data = payment.json()

    assert data["receipt_number"].startswith(
        "REC-"
    )

    assert dec(
        data["plan_total_paid"]
    ) == Decimal("700.00")

    assert dec(
        data[
            "plan_outstanding_amount"
        ]
    ) == Decimal("1700.00")

    detail = await client.get(
        (
            "/api/v1/installments/"
            f"{plan['id']}"
        ),
        headers=admin_headers,
    )

    assert detail.status_code == 200

    schedules = (
        detail.json()["schedules"]
    )

    assert schedules[0]["status"] == (
        "paid"
    )

    assert schedules[1]["status"] == (
        "partial"
    )

    db_payment = await db_session.get(
        CustomerPayment,
        data["payment_id"],
    )

    assert db_payment is not None

    assert (
        db_payment.invoice_id
        == invoice["id"]
    )


@pytest.mark.asyncio
async def test_generic_payment_blocked_for_active_plan(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="813",
        )
    )

    invoice = fixture["confirmed"]

    await create_plan(
        client,
        admin_headers,
        invoice["id"],
    )

    response = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice["id"],
            "amount":
                "100.00",
            "payment_method":
                "cash",
        },
    )

    assert response.status_code == 409

    assert (
        "installment"
        in response.json()["detail"].lower()
    )


@pytest.mark.asyncio
async def test_installment_payment_reversal_restores_balances(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="814",
        )
    )

    invoice = fixture["confirmed"]

    customer_id = (
        fixture["customer"]["id"]
    )

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
    )

    payment_response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount":
                "600.00",
            "payment_method":
                "bank_transfer",
            "reference_number":
                "BANK-814",
        },
    )

    assert (
        payment_response.status_code
        == 201
    )

    payment = payment_response.json()

    reverse = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments/"
            f"{payment['payment_id']}/"
            "reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Installment correction",
        },
    )

    assert reverse.status_code == 200, (
        reverse.text
    )

    reversed_data = reverse.json()

    assert dec(
        reversed_data[
            "plan_total_paid"
        ]
    ) == Decimal("0.00")

    assert dec(
        reversed_data[
            "plan_outstanding_amount"
        ]
    ) == Decimal("2400.00")

    payment_row = await db_session.get(
        CustomerPayment,
        payment["payment_id"],
    )

    assert payment_row is not None

    assert payment_row.is_reversed is True

    allocation_result = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation
                .payment_id
                == payment["payment_id"]
            )
        )
    )

    allocations = (
        allocation_result.scalars().all()
    )

    assert allocations

    assert all(
        item.is_reversed
        for item in allocations
    )

    customer = await db_session.get(
        Customer,
        customer_id,
    )

    assert customer is not None

    assert dec(
        customer.current_balance
    ) == Decimal("2400.00")


@pytest.mark.asyncio
async def test_overdue_schedule_detection(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="815",
        )
    )

    invoice = fixture["confirmed"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=3,
        first_due=(
            date.today()
            - timedelta(days=40)
        ),
    )

    detail = await client.get(
        (
            "/api/v1/installments/"
            f"{plan['id']}"
        ),
        headers=admin_headers,
    )

    assert detail.status_code == 200

    data = detail.json()

    assert (
        data[
            "overdue_installment_count"
        ]
        >= 1
    )

    assert dec(
        data["overdue_amount"]
    ) > Decimal("0.00")


@pytest.mark.asyncio
async def test_customer_ledger_and_statement(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="816",
        )
    )

    invoice = fixture["confirmed"]

    customer_id = (
        fixture["customer"]["id"]
    )

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
    )

    payment = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount":
                "500.00",
            "payment_method":
                "cash",
        },
    )

    assert payment.status_code == 201

    ledger = await client.get(
        (
            "/api/v1/installments/"
            f"customers/{customer_id}/"
            "ledger"
        ),
        headers=admin_headers,
    )

    assert ledger.status_code == 200, (
        ledger.text
    )

    ledger_data = ledger.json()

    types = {
        entry["transaction_type"]
        for entry
        in ledger_data["entries"]
    }

    assert "sales_invoice" in types
    assert "payment" in types

    assert dec(
        ledger_data[
            "closing_balance"
        ]
    ) == Decimal("1900.00")

    statement = await client.get(
        (
            "/api/v1/installments/"
            f"customers/{customer_id}/"
            "statement"
        ),
        headers=admin_headers,
    )

    assert (
        statement.status_code
        == 200
    )

    assert (
        statement.json()[
            "customer_id"
        ]
        == customer_id
    )

    assert (
        statement.json()[
            "generated_at"
        ]
        is not None
    )


@pytest.mark.asyncio
async def test_installment_plan_cannot_duplicate_invoice(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="817",
        )
    )

    invoice = fixture["confirmed"]

    await create_plan(
        client,
        admin_headers,
        invoice["id"],
    )

    duplicate = await client.post(
        "/api/v1/installments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice["id"],
            "first_due_date":
                (
                    date.today()
                    + timedelta(days=30)
                ).isoformat(),
            "frequency":
                "monthly",
            "installment_count":
                4,
        },
    )

    assert duplicate.status_code == 409
