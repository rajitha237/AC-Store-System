from decimal import Decimal

import pytest
from sqlalchemy import func, select

import app.services.credit_note as credit_note_service
import app.services.payment_service as payment_service
import app.services.sales_service as sales_service
import app.services.service as service_service

from app.models import (
    AuditLog,
    Customer,
    CustomerPayment,
    SalesInvoice,
    SalesReturn,
    StockItem,
    StockMovement,
    User,
)
from app.models.credit_note import (
    CreditNote,
    CustomerRefund,
)
from app.schemas.credit_note import (
    FinancialReversalRequest,
)
from app.schemas.payment import (
    PaymentReceiveRequest,
    PaymentReverseRequest,
)
from app.schemas.sales import (
    SalesInvoiceConfirmRequest,
)
from app.schemas.service import (
    ServicePartCreate,
)

from tests.test_inventory import (
    create_product,
    get_warehouse,
    receive_non_serialized,
)
from tests.test_returns_credit_notes import (
    create_approve_post_credit_note,
    get_returned_warehouse,
    prepare_refund_return,
    stock_quantity,
)
from tests.test_sales_payments import (
    confirm_invoice,
    create_sales_fixture,
)
from tests.test_service import (
    create_customer as create_service_customer,
    create_job,
    move_to_approved,
)


class InjectedAtomicityFailure(
    RuntimeError
):
    pass


async def fail_audit(
    *args,
    **kwargs,
):
    raise InjectedAtomicityFailure(
        "intentional atomicity failure"
    )


def dec(value) -> Decimal:
    return Decimal(str(value))


async def get_admin_user(
    db_session,
) -> User:
    result = await db_session.execute(
        select(User)
        .where(
            User.is_superuser.is_(True)
        )
        .order_by(User.id)
    )

    user = result.scalars().first()

    assert user is not None

    return user


async def audit_count(
    db_session,
) -> int:
    value = await db_session.scalar(
        select(
            func.count(AuditLog.id)
        )
    )

    return int(value or 0)


async def movement_count(
    db_session,
) -> int:
    value = await db_session.scalar(
        select(
            func.count(
                StockMovement.id
            )
        )
    )

    return int(value or 0)


async def payment_count_for_invoice(
    db_session,
    invoice_id: int,
) -> int:
    value = await db_session.scalar(
        select(
            func.count(
                CustomerPayment.id
            )
        )
        .where(
            CustomerPayment.invoice_id
            == invoice_id
        )
    )

    return int(value or 0)


async def fresh_invoice(
    db_session,
    invoice_id: int,
) -> SalesInvoice:
    result = await db_session.execute(
        select(SalesInvoice)
        .where(
            SalesInvoice.id == invoice_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    invoice = result.scalar_one()

    return invoice


async def fresh_customer(
    db_session,
    customer_id: int,
) -> Customer:
    result = await db_session.execute(
        select(Customer)
        .where(
            Customer.id == customer_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    customer = result.scalar_one()

    return customer


async def fresh_stock(
    db_session,
    *,
    product_id: int,
    warehouse_id: int,
) -> StockItem:
    result = await db_session.execute(
        select(StockItem)
        .where(
            StockItem.product_id
            == product_id,
            StockItem.warehouse_id
            == warehouse_id,
        )
        .execution_options(
            populate_existing=True
        )
    )

    return result.scalar_one()


@pytest.mark.asyncio
async def test_sales_confirm_rolls_back_everything_when_audit_fails(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="601",
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice_id = fixture["invoice"]["id"]
    customer_id = fixture["customer"]["id"]
    product_id = fixture["product"]["id"]
    warehouse_id = fixture["warehouse"]["id"]

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_before = await fresh_customer(
        db_session,
        customer_id,
    )

    stock_before = await fresh_stock(
        db_session,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )

    state_before = {
        "invoice_status":
            invoice_before.invoice_status,
        "payment_status":
            invoice_before.payment_status,
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "customer_balance":
            dec(customer_before.current_balance),
        "stock":
            dec(stock_before.quantity_on_hand),
        "movements":
            await movement_count(
                db_session
            ),
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        sales_service,
        "create_audit_log",
        fail_audit,
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await sales_service.confirm_invoice(
            session=db_session,
            invoice_id=invoice_id,
            payload=SalesInvoiceConfirmRequest(),
            current_user=admin,
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_after = await fresh_customer(
        db_session,
        customer_id,
    )

    stock_after = await fresh_stock(
        db_session,
        product_id=product_id,
        warehouse_id=warehouse_id,
    )

    assert (
        invoice_after.invoice_status
        == state_before["invoice_status"]
    )

    assert (
        invoice_after.payment_status
        == state_before["payment_status"]
    )

    assert dec(
        invoice_after.paid_amount
    ) == state_before["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == state_before["balance_amount"]

    assert dec(
        customer_after.current_balance
    ) == state_before["customer_balance"]

    assert dec(
        stock_after.quantity_on_hand
    ) == state_before["stock"]

    assert (
        await movement_count(db_session)
        == state_before["movements"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )

    assert (
        await payment_count_for_invoice(
            db_session,
            invoice_id,
        )
        == 0
    )


@pytest.mark.asyncio
async def test_payment_receive_rolls_back_invoice_customer_and_payment(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="602",
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice_id = fixture["invoice"]["id"]

    confirmed_response = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirmed_response.status_code == 200

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_before = await fresh_customer(
        db_session,
        invoice_before.customer_id,
    )

    state_before = {
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "customer_balance":
            dec(customer_before.current_balance),
        "payments":
            await payment_count_for_invoice(
                db_session,
                invoice_id,
            ),
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        payment_service,
        "create_audit_log",
        fail_audit,
    )

    payload = PaymentReceiveRequest(
        invoice_id=invoice_id,
        amount=Decimal("400.00"),
        payment_method="cash",
        reference_number="ATOMIC-602",
        notes="Atomicity failure test",
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await (
            payment_service
            .receive_invoice_payment(
                session=db_session,
                payload=payload,
                current_user=admin,
            )
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_after = await fresh_customer(
        db_session,
        invoice_after.customer_id,
    )

    assert dec(
        invoice_after.paid_amount
    ) == state_before["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == state_before["balance_amount"]

    assert (
        invoice_after.payment_status
        == state_before["payment_status"]
    )

    assert dec(
        customer_after.current_balance
    ) == state_before["customer_balance"]

    assert (
        await payment_count_for_invoice(
            db_session,
            invoice_id,
        )
        == state_before["payments"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )


@pytest.mark.asyncio
async def test_payment_reverse_rolls_back_all_financial_state(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="603",
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice_id = fixture["invoice"]["id"]

    confirmed = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirmed.status_code == 200

    payment_response = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "400.00",
            "payment_method":
                "cash",
            "reference_number":
                "ATOMIC-PAY-603",
            "notes":
                "Payment reversal atomicity",
        },
    )

    assert payment_response.status_code == 201, (
        payment_response.text
    )

    payment_id = (
        payment_response.json()
        ["payment"]["id"]
    )

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_before = await fresh_customer(
        db_session,
        invoice_before.customer_id,
    )

    payment_before = await db_session.get(
        CustomerPayment,
        payment_id,
    )

    assert payment_before is not None

    state_before = {
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "customer_balance":
            dec(customer_before.current_balance),
        "is_reversed":
            payment_before.is_reversed,
        "reversed_at":
            payment_before.reversed_at,
        "reason":
            payment_before.reversal_reason,
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        payment_service,
        "create_audit_log",
        fail_audit,
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await (
            payment_service
            .reverse_invoice_payment(
                session=db_session,
                payment_id=payment_id,
                payload=PaymentReverseRequest(
                    reason=(
                        "Injected reversal "
                        "atomicity failure"
                    )
                ),
                current_user=admin,
            )
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_after = await fresh_customer(
        db_session,
        invoice_after.customer_id,
    )

    payment_after = await db_session.get(
        CustomerPayment,
        payment_id,
        populate_existing=True,
    )

    assert payment_after is not None

    assert dec(
        invoice_after.paid_amount
    ) == state_before["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == state_before["balance_amount"]

    assert (
        invoice_after.payment_status
        == state_before["payment_status"]
    )

    assert dec(
        customer_after.current_balance
    ) == state_before["customer_balance"]

    assert (
        payment_after.is_reversed
        == state_before["is_reversed"]
    )

    assert (
        payment_after.reversed_at
        == state_before["reversed_at"]
    )

    assert (
        payment_after.reversal_reason
        == state_before["reason"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )


@pytest.mark.asyncio
async def test_service_part_issue_rolls_back_stock_and_job_part(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    customer = await create_service_customer(
        client,
        admin_headers,
        suffix="604",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="604",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    receive_response = (
        await receive_non_serialized(
            client,
            admin_headers,
            product_id=product["id"],
            warehouse_id=warehouse["id"],
            quantity="10.000",
            unit_cost="100.00",
            reference_id="ATOMIC-SERVICE-604",
        )
    )

    assert receive_response.status_code == 201

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="604",
        product_id=product["id"],
    )

    await move_to_approved(
        client,
        admin_headers,
        job["id"],
    )

    stock_before = await fresh_stock(
        db_session,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
    )

    state_before = {
        "stock":
            dec(stock_before.quantity_on_hand),
        "movements":
            await movement_count(
                db_session
            ),
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        service_service,
        "recalculate_service_totals",
        fail_audit,
    )

    payload = ServicePartCreate(
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity=Decimal("2.000"),
        unit_price=Decimal("175.00"),
        notes="Atomic service part test",
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await service_service.add_service_part(
            session=db_session,
            job_id=job["id"],
            payload=payload,
            current_user=admin,
        )

    stock_after = await fresh_stock(
        db_session,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
    )

    assert dec(
        stock_after.quantity_on_hand
    ) == state_before["stock"]

    assert (
        await movement_count(db_session)
        == state_before["movements"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )

    detail_response = await client.get(
        f"/api/v1/service/jobs/{job['id']}",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["parts"] == []

    assert dec(
        detail["parts_total"]
    ) == Decimal("0.00")


@pytest.mark.asyncio
async def test_refund_post_rolls_back_invoice_return_and_refund(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="605",
        fully_paid=True,
    )

    credit_note = (
        await create_approve_post_credit_note(
            client,
            admin_headers,
            return_id=
                fixture["return"]["id"],
        )
    )

    refund_response = await client.post(
        "/api/v1/credit-notes/refunds",
        headers=admin_headers,
        json={
            "credit_note_id":
                credit_note["id"],
            "amount":
                "1200.00",
            "refund_method":
                "cash",
            "reference_number":
                "ATOMIC-REFUND-605",
            "notes":
                "Refund atomicity test",
        },
    )

    assert refund_response.status_code == 201, (
        refund_response.text
    )

    refund_id = refund_response.json()["id"]

    invoice_id = fixture["invoice"]["id"]
    return_id = fixture["return"]["id"]

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    sales_return_before = (
        await db_session.get(
            SalesReturn,
            return_id,
        )
    )

    refund_before = await db_session.get(
        CustomerRefund,
        refund_id,
    )

    assert sales_return_before is not None
    assert refund_before is not None

    state_before = {
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "return_status":
            sales_return_before.status,
        "completed_at":
            sales_return_before.completed_at,
        "refund_status":
            refund_before.status,
        "refund_reversed":
            refund_before.is_reversed,
        "refund_posted_at":
            refund_before.posted_at,
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        credit_note_service,
        "create_audit_log",
        fail_audit,
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await credit_note_service.post_refund(
            session=db_session,
            refund_id=refund_id,
            current_user=admin,
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    sales_return_after = await db_session.get(
        SalesReturn,
        return_id,
        populate_existing=True,
    )

    refund_after = await db_session.get(
        CustomerRefund,
        refund_id,
        populate_existing=True,
    )

    assert sales_return_after is not None
    assert refund_after is not None

    assert dec(
        invoice_after.paid_amount
    ) == state_before["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == state_before["balance_amount"]

    assert (
        invoice_after.payment_status
        == state_before["payment_status"]
    )

    assert (
        sales_return_after.status
        == state_before["return_status"]
    )

    assert (
        sales_return_after.completed_at
        == state_before["completed_at"]
    )

    assert (
        refund_after.status
        == state_before["refund_status"]
    )

    assert (
        refund_after.is_reversed
        == state_before["refund_reversed"]
    )

    assert (
        refund_after.posted_at
        == state_before["refund_posted_at"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )


@pytest.mark.asyncio
async def test_credit_note_reverse_rolls_back_stock_and_financial_state(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="606",
        fully_paid=True,
    )

    credit_note_data = (
        await create_approve_post_credit_note(
            client,
            admin_headers,
            return_id=
                fixture["return"]["id"],
        )
    )

    credit_note_id = credit_note_data["id"]
    invoice_id = fixture["invoice"]["id"]
    return_id = fixture["return"]["id"]
    product_id = fixture["product"]["id"]

    returned_warehouse = (
        await get_returned_warehouse(
            client,
            admin_headers,
        )
    )

    returned_warehouse_id = (
        returned_warehouse["id"]
    )

    returned_stock_before = (
        await stock_quantity(
            db_session,
            product_id=product_id,
            warehouse_id=
                returned_warehouse_id,
        )
    )

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    credit_before = await db_session.get(
        CreditNote,
        credit_note_id,
    )

    sales_return_before = (
        await db_session.get(
            SalesReturn,
            return_id,
        )
    )

    assert credit_before is not None
    assert sales_return_before is not None

    state_before = {
        "credited_amount":
            dec(invoice_before.credited_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "credit_status":
            credit_before.status,
        "credit_reversed":
            credit_before.is_reversed,
        "credit_reversed_at":
            credit_before.reversed_at,
        "return_status":
            sales_return_before.status,
        "return_completed_at":
            sales_return_before.completed_at,
        "returned_stock":
            returned_stock_before,
        "movements":
            await movement_count(
                db_session
            ),
        "audits":
            await audit_count(
                db_session
            ),
    }

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        credit_note_service,
        "create_audit_log",
        fail_audit,
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await (
            credit_note_service
            .reverse_credit_note(
                session=db_session,
                credit_note_id=
                    credit_note_id,
                payload=(
                    FinancialReversalRequest(
                        reason=(
                            "Injected credit "
                            "reversal failure"
                        )
                    )
                ),
                current_user=admin,
            )
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    credit_after = await db_session.get(
        CreditNote,
        credit_note_id,
        populate_existing=True,
    )

    sales_return_after = await db_session.get(
        SalesReturn,
        return_id,
        populate_existing=True,
    )

    returned_stock_after = (
        await stock_quantity(
            db_session,
            product_id=product_id,
            warehouse_id=
                returned_warehouse_id,
        )
    )

    assert credit_after is not None
    assert sales_return_after is not None

    assert dec(
        invoice_after.credited_amount
    ) == state_before["credited_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == state_before["balance_amount"]

    assert (
        invoice_after.payment_status
        == state_before["payment_status"]
    )

    assert (
        credit_after.status
        == state_before["credit_status"]
    )

    assert (
        credit_after.is_reversed
        == state_before["credit_reversed"]
    )

    assert (
        credit_after.reversed_at
        == state_before["credit_reversed_at"]
    )

    assert (
        sales_return_after.status
        == state_before["return_status"]
    )

    assert (
        sales_return_after.completed_at
        == state_before[
            "return_completed_at"
        ]
    )

    assert (
        returned_stock_after
        == state_before["returned_stock"]
    )

    assert (
        await movement_count(db_session)
        == state_before["movements"]
    )

    assert (
        await audit_count(db_session)
        == state_before["audits"]
    )
