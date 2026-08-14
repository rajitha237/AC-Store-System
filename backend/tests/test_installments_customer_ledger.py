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
    interest_rate="0.0000",
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
            "interest_rate":
                interest_rate,
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


@pytest.mark.asyncio
async def test_installment_overpayment_rejected_atomically(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="819",
        )
    )

    invoice = fixture["confirmed"]
    customer_id = fixture["customer"]["id"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
    )

    plan_id = plan["id"]

    assert plan["status"] == "active"

    outstanding_before = dec(
        plan["outstanding_amount"]
    )

    assert outstanding_before == Decimal(
        "2400.00"
    )

    payment_count_before = (
        await db_session.execute(
            select(CustomerPayment).where(
                CustomerPayment.invoice_id
                == invoice["id"]
            )
        )
    ).scalars().all()

    allocation_count_before = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation.plan_id
                == plan_id
            )
        )
    ).scalars().all()

    db_plan_before = await db_session.get(
        InstallmentPlan,
        plan_id,
    )

    db_invoice_before = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )

    db_customer_before = await db_session.get(
        Customer,
        customer_id,
    )

    assert db_plan_before is not None
    assert db_invoice_before is not None
    assert db_customer_before is not None

    plan_total_paid_before = dec(
        db_plan_before.total_paid
    )

    plan_outstanding_before = dec(
        db_plan_before.outstanding_amount
    )

    invoice_paid_before = dec(
        db_invoice_before.paid_amount
    )

    invoice_balance_before = dec(
        db_invoice_before.balance_amount
    )

    customer_balance_before = dec(
        db_customer_before.current_balance
    )

    response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan_id}/payments"
        ),
        headers=admin_headers,
        json={
            "amount": "2400.01",
            "payment_method": "cash",
            "reference_number":
                "INSTALLMENT-OVERPAY-TEST",
            "notes":
                "Atomic installment overpayment test",
        },
    )

    assert response.status_code == 422, (
        response.text
    )

    assert (
        "Payment amount cannot exceed "
        "installment outstanding"
        in response.json()["detail"]
    )

    payment_count_after = (
        await db_session.execute(
            select(CustomerPayment).where(
                CustomerPayment.invoice_id
                == invoice["id"]
            )
        )
    ).scalars().all()

    allocation_count_after = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation.plan_id
                == plan_id
            )
        )
    ).scalars().all()

    await db_session.refresh(
        db_plan_before
    )

    await db_session.refresh(
        db_invoice_before
    )

    await db_session.refresh(
        db_customer_before
    )

    assert (
        len(payment_count_after)
        == len(payment_count_before)
    )

    assert (
        len(allocation_count_after)
        == len(allocation_count_before)
    )

    assert dec(
        db_plan_before.total_paid
    ) == plan_total_paid_before

    assert dec(
        db_plan_before.outstanding_amount
    ) == plan_outstanding_before

    assert (
        db_plan_before.status
        == "active"
    )

    assert dec(
        db_invoice_before.paid_amount
    ) == invoice_paid_before

    assert dec(
        db_invoice_before.balance_amount
    ) == invoice_balance_before

    assert dec(
        db_customer_before.current_balance
    ) == customer_balance_before



@pytest.mark.asyncio
async def test_installment_invoice_balance_inconsistency_rejected_atomically(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix="820",
    )

    invoice = fixture["confirmed"]
    customer_id = fixture["customer"]["id"]

    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
    )

    plan_id = plan["id"]

    db_plan = await db_session.get(
        InstallmentPlan,
        plan_id,
    )
    db_invoice = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )
    db_customer = await db_session.get(
        Customer,
        customer_id,
    )

    assert db_plan is not None
    assert db_invoice is not None
    assert db_customer is not None

    assert dec(
        db_plan.outstanding_amount
    ) == Decimal("2400.00")

    # Create an intentionally inconsistent committed fixture.
    #
    # Installment outstanding = 2400.00
    # Invoice balance          =   50.00
    # Attempted payment        =  100.00
    #
    # Commit is intentional here because the API request uses a
    # separate SQLAlchemy session/SQLite connection. Leaving this
    # write transaction open would lock SQLite during client.post().
    db_invoice.balance_amount = Decimal("50.00")

    await db_session.commit()

    payment_rows_before = (
        await db_session.execute(
            select(CustomerPayment).where(
                CustomerPayment.invoice_id
                == invoice["id"]
            )
        )
    ).scalars().all()

    allocation_rows_before = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation.plan_id
                == plan_id
            )
        )
    ).scalars().all()

    db_plan = await db_session.get(
        InstallmentPlan,
        plan_id,
    )
    db_invoice = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )
    db_customer = await db_session.get(
        Customer,
        customer_id,
    )

    assert db_plan is not None
    assert db_invoice is not None
    assert db_customer is not None

    plan_paid_before = dec(
        db_plan.total_paid
    )
    plan_outstanding_before = dec(
        db_plan.outstanding_amount
    )
    invoice_paid_before = dec(
        db_invoice.paid_amount
    )
    invoice_balance_before = dec(
        db_invoice.balance_amount
    )
    customer_balance_before = dec(
        db_customer.current_balance
    )

    response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan_id}/payments"
        ),
        headers=admin_headers,
        json={
            "amount": "100.00",
            "payment_method": "cash",
            "reference_number":
                "INSTALLMENT-INCONSISTENCY-TEST",
            "notes":
                "Atomic invoice balance inconsistency test",
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    assert response.json()["detail"] == (
        "Installment plan and invoice "
        "principal balances are inconsistent"
    )

    # Expire cached ORM state so all post-request checks are
    # re-read from the database.
    db_session.expire_all()

    payment_rows_after = (
        await db_session.execute(
            select(CustomerPayment).where(
                CustomerPayment.invoice_id
                == invoice["id"]
            )
        )
    ).scalars().all()

    allocation_rows_after = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation.plan_id
                == plan_id
            )
        )
    ).scalars().all()

    db_plan_after = await db_session.get(
        InstallmentPlan,
        plan_id,
    )
    db_invoice_after = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )
    db_customer_after = await db_session.get(
        Customer,
        customer_id,
    )

    assert db_plan_after is not None
    assert db_invoice_after is not None
    assert db_customer_after is not None

    assert (
        len(payment_rows_after)
        == len(payment_rows_before)
    )

    assert (
        len(allocation_rows_after)
        == len(allocation_rows_before)
    )

    assert dec(
        db_plan_after.total_paid
    ) == plan_paid_before

    assert dec(
        db_plan_after.outstanding_amount
    ) == plan_outstanding_before

    assert dec(
        db_invoice_after.paid_amount
    ) == invoice_paid_before

    assert dec(
        db_invoice_after.balance_amount
    ) == invoice_balance_before

    assert dec(
        db_customer_after.current_balance
    ) == customer_balance_before



@pytest.mark.asyncio
async def test_installment_payment_split_is_proportional_per_schedule(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_confirmed_invoice(
        client,
        admin_headers,
        db_session,
        suffix="822",
    )

    invoice = fixture["confirmed"]

    # The fixture invoice principal is 2,400.00.
    # 10% interest => 240.00.
    # Four schedules => 660.00 each.
    plan = await create_plan(
        client,
        admin_headers,
        invoice["id"],
        count=4,
        interest_rate="10.0000",
    )

    response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount": "660.00",
            "payment_method": "cash",
            "reference_number":
                "PROPORTIONAL-SPLIT-660",
            "notes":
                "Proportional installment split test",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    payment = response.json()

    assert dec(
        payment["principal_amount"]
    ) == Decimal("600.00")

    assert dec(
        payment["interest_amount"]
    ) == Decimal("60.00")

    allocation_result = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation
                .payment_id
                == payment["payment_id"],
                InstallmentPaymentAllocation
                .is_reversed
                .is_(False),
            )
        )
    )

    allocations = (
        allocation_result.scalars().all()
    )

    assert len(allocations) == 1

    allocation = allocations[0]

    assert dec(
        allocation.amount
    ) == Decimal("660.00")

    assert dec(
        allocation.principal_amount
    ) == Decimal("600.00")

    assert dec(
        allocation.interest_amount
    ) == Decimal("60.00")

    assert (
        allocation.schedule_id
        == plan["schedules"][0]["id"]
    )

    assert (
        plan["schedules"][0][
            "installment_number"
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_installment_interest_principal_payment_reversal_ledger(
    client,
    admin_headers,
    db_session,
):
    fixture = (
        await create_confirmed_invoice(
            client,
            admin_headers,
            db_session,
            suffix="821",
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
        count=4,
        interest_rate="10.0000",
    )

    assert dec(
        plan["principal_amount"]
    ) == Decimal("2400.00")

    assert Decimal(
        str(plan["interest_rate"])
    ) == Decimal("10.0000")

    assert dec(
        plan["interest_amount"]
    ) == Decimal("240.00")

    assert dec(
        plan["financed_amount"]
    ) == Decimal("2640.00")

    assert dec(
        plan["outstanding_amount"]
    ) == Decimal("2640.00")

    schedule_total = sum(
        (
            dec(item["amount_due"])
            for item
            in plan["schedules"]
        ),
        Decimal("0.00"),
    )

    assert schedule_total == Decimal(
        "2640.00"
    )

    db_session.expire_all()

    customer_after_plan = (
        await db_session.get(
            Customer,
            customer_id,
        )
    )

    assert customer_after_plan is not None

    assert dec(
        customer_after_plan.current_balance
    ) == Decimal("2640.00")

    payment_response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments"
        ),
        headers=admin_headers,
        json={
            "amount":
                "2500.00",
            "payment_method":
                "cash",
            "reference_number":
                "INTEREST-10-PAYMENT",
            "notes":
                "10 percent interest lifecycle test",
        },
    )

    assert (
        payment_response.status_code
        == 201
    ), payment_response.text

    payment = payment_response.json()

    assert dec(
        payment["amount"]
    ) == Decimal("2500.00")

    assert dec(
        payment["principal_amount"]
    ) == Decimal("2272.73")

    assert dec(
        payment["interest_amount"]
    ) == Decimal("227.27")

    assert dec(
        payment["plan_total_paid"]
    ) == Decimal("2500.00")

    assert dec(
        payment[
            "plan_outstanding_amount"
        ]
    ) == Decimal("140.00")

    assert dec(
        payment[
            "invoice_paid_amount"
        ]
    ) == Decimal("2272.73")

    assert dec(
        payment[
            "invoice_balance_amount"
        ]
    ) == Decimal("127.27")

    assert dec(
        payment["customer_balance"]
    ) == Decimal("140.00")

    allocation_result = (
        await db_session.execute(
            select(
                InstallmentPaymentAllocation
            ).where(
                InstallmentPaymentAllocation
                .payment_id
                == payment["payment_id"],
                InstallmentPaymentAllocation
                .is_reversed
                .is_(False),
            )
        )
    )

    allocations = (
        allocation_result
        .scalars()
        .all()
    )

    assert allocations

    allocation_amount = sum(
        (
            dec(item.amount)
            for item in allocations
        ),
        Decimal("0.00"),
    )

    allocation_principal = sum(
        (
            dec(
                item.principal_amount
            )
            for item in allocations
        ),
        Decimal("0.00"),
    )

    allocation_interest = sum(
        (
            dec(
                item.interest_amount
            )
            for item in allocations
        ),
        Decimal("0.00"),
    )

    assert allocation_amount == Decimal(
        "2500.00"
    )

    assert allocation_principal == Decimal(
        "2272.73"
    )

    assert allocation_interest == Decimal(
        "227.27"
    )

    ledger_response = await client.get(
        (
            "/api/v1/installments/"
            f"customers/{customer_id}/"
            "ledger"
        ),
        headers=admin_headers,
    )

    assert (
        ledger_response.status_code
        == 200
    ), ledger_response.text

    ledger = ledger_response.json()

    interest_entries = [
        entry
        for entry in ledger["entries"]
        if (
            entry["transaction_type"]
            == "installment_interest"
            and entry["reference"]
            == plan["agreement_number"]
        )
    ]

    assert len(interest_entries) == 1

    assert dec(
        interest_entries[0]["debit"]
    ) == Decimal("240.00")

    assert dec(
        interest_entries[0]["credit"]
    ) == Decimal("0.00")

    assert dec(
        ledger["closing_balance"]
    ) == Decimal("140.00")

    db_session.expire_all()

    db_invoice = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )

    db_customer = await db_session.get(
        Customer,
        customer_id,
    )

    db_plan = await db_session.get(
        InstallmentPlan,
        plan["id"],
    )

    assert db_invoice is not None
    assert db_customer is not None
    assert db_plan is not None

    assert dec(
        db_invoice.paid_amount
    ) == Decimal("2272.73")

    assert dec(
        db_invoice.balance_amount
    ) == Decimal("127.27")

    assert dec(
        db_customer.current_balance
    ) == Decimal("140.00")

    assert dec(
        db_plan.outstanding_amount
    ) == Decimal("140.00")

    reverse_response = await client.post(
        (
            "/api/v1/installments/"
            f"{plan['id']}/payments/"
            f"{payment['payment_id']}/"
            "reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Interest lifecycle reversal",
        },
    )

    assert (
        reverse_response.status_code
        == 200
    ), reverse_response.text

    reversed_data = (
        reverse_response.json()
    )

    assert dec(
        reversed_data[
            "principal_amount"
        ]
    ) == Decimal("2272.73")

    assert dec(
        reversed_data[
            "interest_amount"
        ]
    ) == Decimal("227.27")

    assert dec(
        reversed_data[
            "plan_total_paid"
        ]
    ) == Decimal("0.00")

    assert dec(
        reversed_data[
            "plan_outstanding_amount"
        ]
    ) == Decimal("2640.00")

    assert dec(
        reversed_data[
            "invoice_paid_amount"
        ]
    ) == Decimal("0.00")

    assert dec(
        reversed_data[
            "invoice_balance_amount"
        ]
    ) == Decimal("2400.00")

    assert dec(
        reversed_data[
            "customer_balance"
        ]
    ) == Decimal("2640.00")

    db_session.expire_all()

    reversed_allocations_result = (
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

    reversed_allocations = (
        reversed_allocations_result
        .scalars()
        .all()
    )

    assert reversed_allocations

    assert all(
        item.is_reversed
        for item
        in reversed_allocations
    )

    ledger_after_reversal_response = (
        await client.get(
            (
                "/api/v1/installments/"
                f"customers/{customer_id}/"
                "ledger"
            ),
            headers=admin_headers,
        )
    )

    assert (
        ledger_after_reversal_response
        .status_code
        == 200
    )

    ledger_after_reversal = (
        ledger_after_reversal_response
        .json()
    )

    assert dec(
        ledger_after_reversal[
            "closing_balance"
        ]
    ) == Decimal("2640.00")

    payment_entries = [
        entry
        for entry
        in ledger_after_reversal[
            "entries"
        ]
        if (
            entry["payment_id"]
            == payment["payment_id"]
        )
    ]

    assert payment_entries == []
