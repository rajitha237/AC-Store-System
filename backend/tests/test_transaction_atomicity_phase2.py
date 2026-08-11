from decimal import Decimal

import pytest
from sqlalchemy import func, select

import app.services.credit_note as credit_note_service
import app.services.returns as returns_service

from app.models import (
    AuditLog,
    Customer,
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
from app.models.returns import (
    SalesReturnItem,
    SalesReturnStatusHistory,
)
from app.schemas.credit_note import (
    FinancialReversalRequest,
)
from app.schemas.returns import (
    ReplacementItemRequest,
)

from tests.test_returns_credit_notes import (
    create_approve_post_credit_note,
    create_return,
    get_returned_warehouse,
    inspect_return,
    prepare_refund_return,
    stock_quantity,
)
from tests.test_sales_payments import (
    confirm_invoice,
    create_sales_fixture,
)
from tests.test_transaction_atomicity import (
    InjectedAtomicityFailure,
    audit_count,
    dec,
    fail_audit,
    fresh_customer,
    fresh_invoice,
    get_admin_user,
    movement_count,
)


RETURNS_URL = "/api/v1/returns"
CREDIT_URL = "/api/v1/credit-notes"


async def status_history_count(
    db_session,
    return_id: int,
) -> int:
    value = await db_session.scalar(
        select(
            func.count(
                SalesReturnStatusHistory.id
            )
        )
        .where(
            SalesReturnStatusHistory.return_id
            == return_id
        )
    )

    return int(value or 0)


async def fresh_return(
    db_session,
    return_id: int,
) -> SalesReturn:
    result = await db_session.execute(
        select(SalesReturn)
        .where(
            SalesReturn.id == return_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    return result.scalar_one()


async def fresh_return_item(
    db_session,
    return_item_id: int,
) -> SalesReturnItem:
    result = await db_session.execute(
        select(SalesReturnItem)
        .where(
            SalesReturnItem.id
            == return_item_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    return result.scalar_one()


async def fresh_credit_note(
    db_session,
    credit_note_id: int,
) -> CreditNote:
    result = await db_session.execute(
        select(CreditNote)
        .where(
            CreditNote.id == credit_note_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    return result.scalar_one()


async def fresh_refund(
    db_session,
    refund_id: int,
) -> CustomerRefund:
    result = await db_session.execute(
        select(CustomerRefund)
        .where(
            CustomerRefund.id == refund_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    return result.scalar_one()


async def create_replacement_return_fixture(
    client,
    admin_headers,
    db_session,
    *,
    suffix: str,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice_id = fixture["invoice"]["id"]

    confirm_response = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirm_response.status_code == 200, (
        confirm_response.text
    )

    invoice_response = await client.get(
        f"/api/v1/sales/invoices/{invoice_id}",
        headers=admin_headers,
    )

    assert invoice_response.status_code == 200

    invoice = invoice_response.json()

    assert len(invoice["items"]) == 1

    invoice_item = invoice["items"][0]

    sales_return = await create_return(
        client,
        admin_headers,
        invoice_id=invoice_id,
        invoice_item_id=invoice_item["id"],
        quantity="1.000",
        reason=(
            "Atomic replacement return "
            "integration test"
        ),
    )

    inspected = await inspect_return(
        client,
        admin_headers,
        sales_return["id"],
    )

    assert inspected["status"] in {
        "inspection",
        "waiting_approval",
    }

    approval_response = await client.post(
        (
            f"{RETURNS_URL}/"
            f"{sales_return['id']}/approval"
        ),
        headers=admin_headers,
        json={
            "approved":
                True,
            "resolution":
                "replacement",
            "approval_notes":
                (
                    "Approved for atomic "
                    "replacement testing"
                ),
            "refund_amount":
                "0.00",
        },
    )

    assert approval_response.status_code == 200, (
        approval_response.text
    )

    approved = approval_response.json()

    assert approved["status"] == "approved"
    assert approved["resolution"] == "replacement"
    assert len(approved["items"]) == 1

    fixture["invoice"] = invoice
    fixture["invoice_item"] = invoice_item
    fixture["return"] = approved
    fixture["return_item"] = approved["items"][0]

    return fixture


async def create_approved_credit_note(
    client,
    admin_headers,
    *,
    return_id: int,
):
    create_response = await client.post(
        CREDIT_URL,
        headers=admin_headers,
        json={
            "return_id":
                return_id,
            "notes":
                "Atomic credit note test",
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    credit_note = create_response.json()

    assert credit_note["status"] == "draft"

    approval_response = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/approval"
        ),
        headers=admin_headers,
        json={
            "notes":
                "Atomic credit note approval",
        },
    )

    assert approval_response.status_code == 200, (
        approval_response.text
    )

    approved = approval_response.json()

    assert approved["status"] == "approved"

    return approved


@pytest.mark.asyncio
async def test_return_processing_rolls_back_stock_status_history_and_movement(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = (
        await create_replacement_return_fixture(
            client,
            admin_headers,
            db_session,
            suffix="701",
        )
    )

    sales_return = fixture["return"]

    return_id = sales_return["id"]
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

    stock_before = await stock_quantity(
        db_session,
        product_id=product_id,
        warehouse_id=returned_warehouse_id,
    )

    return_before = await fresh_return(
        db_session,
        return_id,
    )

    history_before = await status_history_count(
        db_session,
        return_id,
    )

    movements_before = await movement_count(
        db_session
    )

    audits_before = await audit_count(
        db_session
    )

    item_before = await fresh_return_item(
        db_session,
        fixture["return_item"]["id"],
    )

    stock_movement_before = (
        item_before.stock_movement_id
    )

    admin = await get_admin_user(
        db_session
    )

    monkeypatch.setattr(
        returns_service,
        "create_audit_log",
        fail_audit,
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await returns_service.process_return(
            session=db_session,
            return_id=return_id,
            current_user=admin,
        )

    return_after = await fresh_return(
        db_session,
        return_id,
    )

    item_after = await fresh_return_item(
        db_session,
        fixture["return_item"]["id"],
    )

    stock_after = await stock_quantity(
        db_session,
        product_id=product_id,
        warehouse_id=returned_warehouse_id,
    )

    assert return_before.status == "approved"

    assert (
        return_after.status
        == return_before.status
    )

    assert (
        return_after.completed_at
        == return_before.completed_at
    )

    assert (
        item_after.stock_movement_id
        == stock_movement_before
    )

    assert stock_after == stock_before

    assert (
        await movement_count(db_session)
        == movements_before
    )

    assert (
        await status_history_count(
            db_session,
            return_id,
        )
        == history_before
    )

    assert (
        await audit_count(db_session)
        == audits_before
    )


@pytest.mark.asyncio
async def test_replacement_issue_rolls_back_stock_item_movement_and_return_state(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = (
        await create_replacement_return_fixture(
            client,
            admin_headers,
            db_session,
            suffix="702",
        )
    )

    return_id = fixture["return"]["id"]
    return_item_id = (
        fixture["return_item"]["id"]
    )

    product_id = fixture["product"]["id"]
    warehouse_id = fixture["warehouse"]["id"]

    admin = await get_admin_user(
        db_session
    )

    processed = await returns_service.process_return(
        session=db_session,
        return_id=return_id,
        current_user=admin,
    )

    assert processed.status == "processing"

    stock_before_result = (
        await db_session.execute(
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
    )

    stock_before_row = (
        stock_before_result.scalar_one()
    )

    stock_before = dec(
        stock_before_row.quantity_on_hand
    )

    item_before = await fresh_return_item(
        db_session,
        return_item_id,
    )

    return_before = await fresh_return(
        db_session,
        return_id,
    )

    movements_before = await movement_count(
        db_session
    )

    history_before = await status_history_count(
        db_session,
        return_id,
    )

    audits_before = await audit_count(
        db_session
    )

    before_replacement = {
        "replacement_product_id":
            item_before.replacement_product_id,
        "replacement_serial_number_id":
            item_before.replacement_serial_number_id,
        "replacement_stock_movement_id":
            item_before.replacement_stock_movement_id,
    }

    monkeypatch.setattr(
        returns_service,
        "create_audit_log",
        fail_audit,
    )

    payload = ReplacementItemRequest(
        return_item_id=return_item_id,
        replacement_product_id=product_id,
        replacement_serial_number_id=None,
        warehouse_id=warehouse_id,
        notes=(
            "Atomic replacement issue "
            "failure injection"
        ),
    )

    with pytest.raises(
        InjectedAtomicityFailure
    ):
        await returns_service.set_replacement_item(
            session=db_session,
            return_id=return_id,
            payload=payload,
            current_user=admin,
        )

    item_after = await fresh_return_item(
        db_session,
        return_item_id,
    )

    return_after = await fresh_return(
        db_session,
        return_id,
    )

    stock_after_result = (
        await db_session.execute(
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
    )

    stock_after_row = (
        stock_after_result.scalar_one()
    )

    assert dec(
        stock_after_row.quantity_on_hand
    ) == stock_before

    assert (
        item_after.replacement_product_id
        == before_replacement[
            "replacement_product_id"
        ]
    )

    assert (
        item_after.replacement_serial_number_id
        == before_replacement[
            "replacement_serial_number_id"
        ]
    )

    assert (
        item_after.replacement_stock_movement_id
        == before_replacement[
            "replacement_stock_movement_id"
        ]
    )

    assert (
        return_after.status
        == return_before.status
    )

    assert (
        return_after.completed_at
        == return_before.completed_at
    )

    assert (
        await movement_count(db_session)
        == movements_before
    )

    assert (
        await status_history_count(
            db_session,
            return_id,
        )
        == history_before
    )

    assert (
        await audit_count(db_session)
        == audits_before
    )


@pytest.mark.asyncio
async def test_credit_note_post_rolls_back_credit_invoice_customer_return_and_stock(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="703",
        fully_paid=True,
    )

    credit_note = await create_approved_credit_note(
        client,
        admin_headers,
        return_id=fixture["return"]["id"],
    )

    credit_note_id = credit_note["id"]
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
            warehouse_id=returned_warehouse_id,
        )
    )

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_before = await fresh_customer(
        db_session,
        invoice_before.customer_id,
    )

    return_before = await fresh_return(
        db_session,
        return_id,
    )

    credit_before = await fresh_credit_note(
        db_session,
        credit_note_id,
    )

    movements_before = await movement_count(
        db_session
    )

    history_before = await status_history_count(
        db_session,
        return_id,
    )

    audits_before = await audit_count(
        db_session
    )

    snapshot = {
        "credited_amount":
            dec(invoice_before.credited_amount),
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "customer_balance":
            dec(customer_before.current_balance),
        "return_status":
            return_before.status,
        "return_completed_at":
            return_before.completed_at,
        "credit_status":
            credit_before.status,
        "credit_posted_at":
            credit_before.posted_at,
        "credit_is_reversed":
            credit_before.is_reversed,
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
        await credit_note_service.post_credit_note(
            session=db_session,
            credit_note_id=credit_note_id,
            current_user=admin,
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    customer_after = await fresh_customer(
        db_session,
        invoice_after.customer_id,
    )

    return_after = await fresh_return(
        db_session,
        return_id,
    )

    credit_after = await fresh_credit_note(
        db_session,
        credit_note_id,
    )

    returned_stock_after = (
        await stock_quantity(
            db_session,
            product_id=product_id,
            warehouse_id=returned_warehouse_id,
        )
    )

    assert dec(
        invoice_after.credited_amount
    ) == snapshot["credited_amount"]

    assert dec(
        invoice_after.paid_amount
    ) == snapshot["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == snapshot["balance_amount"]

    assert (
        invoice_after.payment_status
        == snapshot["payment_status"]
    )

    assert dec(
        customer_after.current_balance
    ) == snapshot["customer_balance"]

    assert (
        return_after.status
        == snapshot["return_status"]
    )

    assert (
        return_after.completed_at
        == snapshot["return_completed_at"]
    )

    assert (
        credit_after.status
        == snapshot["credit_status"]
    )

    assert (
        credit_after.posted_at
        == snapshot["credit_posted_at"]
    )

    assert (
        credit_after.is_reversed
        == snapshot["credit_is_reversed"]
    )

    assert (
        returned_stock_after
        == returned_stock_before
    )

    assert (
        await movement_count(db_session)
        == movements_before
    )

    assert (
        await status_history_count(
            db_session,
            return_id,
        )
        == history_before
    )

    assert (
        await audit_count(db_session)
        == audits_before
    )


@pytest.mark.asyncio
async def test_refund_reversal_rolls_back_refund_invoice_and_return_state(
    client,
    admin_headers,
    db_session,
    monkeypatch,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="704",
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

    refund_create_response = await client.post(
        f"{CREDIT_URL}/refunds",
        headers=admin_headers,
        json={
            "credit_note_id":
                credit_note["id"],
            "amount":
                "1200.00",
            "refund_method":
                "cash",
            "reference_number":
                "ATOMIC-704",
            "notes":
                "Refund reversal atomicity setup",
        },
    )

    assert (
        refund_create_response.status_code
        == 201
    ), refund_create_response.text

    refund_id = (
        refund_create_response.json()["id"]
    )

    post_response = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund_id}/post"
        ),
        headers=admin_headers,
    )

    assert post_response.status_code == 200, (
        post_response.text
    )

    invoice_id = fixture["invoice"]["id"]
    return_id = fixture["return"]["id"]

    invoice_before = await fresh_invoice(
        db_session,
        invoice_id,
    )

    return_before = await fresh_return(
        db_session,
        return_id,
    )

    refund_before = await fresh_refund(
        db_session,
        refund_id,
    )

    history_before = await status_history_count(
        db_session,
        return_id,
    )

    audits_before = await audit_count(
        db_session
    )

    snapshot = {
        "paid_amount":
            dec(invoice_before.paid_amount),
        "balance_amount":
            dec(invoice_before.balance_amount),
        "payment_status":
            invoice_before.payment_status,
        "return_status":
            return_before.status,
        "return_completed_at":
            return_before.completed_at,
        "refund_status":
            refund_before.status,
        "refund_is_reversed":
            refund_before.is_reversed,
        "refund_reversed_at":
            refund_before.reversed_at,
        "refund_reversal_reason":
            refund_before.reversal_reason,
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
        await credit_note_service.reverse_refund(
            session=db_session,
            refund_id=refund_id,
            payload=FinancialReversalRequest(
                reason=(
                    "Injected refund reversal "
                    "atomicity failure"
                )
            ),
            current_user=admin,
        )

    invoice_after = await fresh_invoice(
        db_session,
        invoice_id,
    )

    return_after = await fresh_return(
        db_session,
        return_id,
    )

    refund_after = await fresh_refund(
        db_session,
        refund_id,
    )

    assert dec(
        invoice_after.paid_amount
    ) == snapshot["paid_amount"]

    assert dec(
        invoice_after.balance_amount
    ) == snapshot["balance_amount"]

    assert (
        invoice_after.payment_status
        == snapshot["payment_status"]
    )

    assert (
        return_after.status
        == snapshot["return_status"]
    )

    assert (
        return_after.completed_at
        == snapshot["return_completed_at"]
    )

    assert (
        refund_after.status
        == snapshot["refund_status"]
    )

    assert (
        refund_after.is_reversed
        == snapshot["refund_is_reversed"]
    )

    assert (
        refund_after.reversed_at
        == snapshot["refund_reversed_at"]
    )

    assert (
        refund_after.reversal_reason
        == snapshot[
            "refund_reversal_reason"
        ]
    )

    assert (
        await status_history_count(
            db_session,
            return_id,
        )
        == history_before
    )

    assert (
        await audit_count(db_session)
        == audits_before
    )
