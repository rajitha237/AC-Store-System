from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import AuditLog, Customer, SalesInvoice, StockItem
from tests.test_sales_payments import (
    confirm_invoice,
    create_sales_fixture,
)


RETURNS_URL = "/api/v1/returns"
CREDIT_URL = "/api/v1/credit-notes"


def dec(value) -> Decimal:
    return Decimal(str(value))


async def get_returned_warehouse(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/inventory/warehouses",
        headers=admin_headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    warehouse = next(
        (
            item
            for item in response.json()
            if item["code"] == "RETURNED"
        ),
        None,
    )

    assert warehouse is not None

    return warehouse


async def stock_quantity(
    db_session,
    *,
    product_id,
    warehouse_id,
):
    result = await db_session.execute(
        select(StockItem)
        .where(
            StockItem.product_id == product_id,
            StockItem.warehouse_id == warehouse_id,
        )
        .execution_options(
            populate_existing=True
        )
    )

    stock = result.scalar_one_or_none()

    if stock is None:
        return Decimal("0.000")

    return dec(
        stock.quantity_on_hand
    )


async def create_confirmed_sale(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
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

    detail_response = await client.get(
        f"/api/v1/sales/invoices/{invoice_id}",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    invoice = detail_response.json()

    assert len(invoice["items"]) == 1

    fixture["invoice"] = invoice
    fixture["invoice_item"] = invoice["items"][0]

    return fixture


async def pay_invoice_in_full(
    client,
    admin_headers,
    *,
    invoice_id,
):
    response = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "2400.00",
            "payment_method":
                "cash",
            "reference_number":
                f"FULL-{invoice_id}",
            "notes":
                "Return integration full payment",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    assert (
        response.json()["payment_status"]
        == "paid"
    )

    return response.json()


async def create_return(
    client,
    admin_headers,
    *,
    invoice_id,
    invoice_item_id,
    quantity="1.000",
    destination_warehouse_id=None,
    reason="Customer requested product return",
):
    item = {
        "invoice_item_id":
            invoice_item_id,
        "quantity":
            quantity,
        "condition":
            "good",
        "reason":
            "Item accepted for return",
    }

    if destination_warehouse_id is not None:
        item["destination_warehouse_id"] = (
            destination_warehouse_id
        )

    response = await client.post(
        RETURNS_URL,
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "return_type":
                "sales_return",
            "reason":
                reason,
            "items": [
                item
            ],
        },
    )

    assert response.status_code == 201, (
        "RETURN CREATE FAILED: "
        f"{response.status_code} "
        f"{response.text}"
    )

    return response.json()


async def inspect_return(
    client,
    admin_headers,
    return_id,
):
    response = await client.post(
        f"{RETURNS_URL}/{return_id}/inspect",
        headers=admin_headers,
        json={
            "inspection_notes":
                "Product inspected and accepted",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    return response.json()


async def approve_refund_return(
    client,
    admin_headers,
    return_id,
    *,
    refund_amount="1200.00",
):
    response = await client.post(
        f"{RETURNS_URL}/{return_id}/approval",
        headers=admin_headers,
        json={
            "approved":
                True,
            "resolution":
                "refund",
            "approval_notes":
                "Approved for customer refund",
            "refund_amount":
                refund_amount,
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    assert data["status"] == "approved"
    assert data["resolution"] == "refund"
    assert dec(
        data["refund_amount"]
    ) == dec(refund_amount)

    return data


async def prepare_refund_return(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
    fully_paid=False,
):
    fixture = await create_confirmed_sale(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
    )

    if fully_paid:
        await pay_invoice_in_full(
            client,
            admin_headers,
            invoice_id=
                fixture["invoice"]["id"],
        )

    sales_return = await create_return(
        client,
        admin_headers,
        invoice_id=
            fixture["invoice"]["id"],
        invoice_item_id=
            fixture["invoice_item"]["id"],
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

    approved = await approve_refund_return(
        client,
        admin_headers,
        sales_return["id"],
    )

    fixture["return"] = approved

    return fixture


async def create_approve_post_credit_note(
    client,
    admin_headers,
    *,
    return_id,
):
    create_response = await client.post(
        CREDIT_URL,
        headers=admin_headers,
        json={
            "return_id":
                return_id,
            "notes":
                "Return integration credit note",
        },
    )

    assert create_response.status_code == 201, (
        "CREDIT NOTE CREATE FAILED: "
        f"{create_response.status_code} "
        f"{create_response.text}"
    )

    credit_note = create_response.json()

    assert credit_note["status"] == "draft"
    assert credit_note["return_id"] == return_id
    assert credit_note["credit_note_number"].startswith(
        "CN-"
    )

    approval_response = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/approval"
        ),
        headers=admin_headers,
        json={
            "notes":
                "Credit note approved in integration test",
        },
    )

    assert approval_response.status_code == 200, (
        approval_response.text
    )

    approved = approval_response.json()

    assert approved["status"] == "approved"
    assert approved["approved_at"] is not None

    post_response = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/post"
        ),
        headers=admin_headers,
    )

    assert post_response.status_code == 200, (
        post_response.text
    )

    posted = post_response.json()

    assert posted["status"] == "posted"
    assert posted["posted_at"] is not None
    assert posted["is_reversed"] is False

    return posted


@pytest.mark.asyncio
async def test_return_create_inspect_approve_and_list(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="401",
        fully_paid=True,
    )

    sales_return = fixture["return"]

    assert sales_return["return_number"].startswith(
        "RET-"
    )
    assert sales_return["invoice_id"] == (
        fixture["invoice"]["id"]
    )
    assert sales_return["status"] == "approved"
    assert sales_return["resolution"] == "refund"
    assert len(sales_return["items"]) == 1

    history = [
        item["new_status"]
        for item in sales_return["status_history"]
    ]

    assert "requested" in history
    assert "approved" in history

    detail_response = await client.get(
        f"{RETURNS_URL}/{sales_return['id']}",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["id"] == sales_return["id"]

    list_response = await client.get(
        RETURNS_URL,
        headers=admin_headers,
        params={
            "search":
                sales_return["return_number"],
            "return_status":
                "approved",
        },
    )

    assert list_response.status_code == 200

    listing = list_response.json()

    assert listing["total"] == 1
    assert (
        listing["items"][0]["id"]
        == sales_return["id"]
    )


@pytest.mark.asyncio
async def test_return_duplicate_invoice_item_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_confirmed_sale(
        client,
        admin_headers,
        db_session,
        suffix="402",
    )

    item_id = fixture["invoice_item"]["id"]

    response = await client.post(
        RETURNS_URL,
        headers=admin_headers,
        json={
            "invoice_id":
                fixture["invoice"]["id"],
            "reason":
                "Duplicate item validation",
            "items": [
                {
                    "invoice_item_id":
                        item_id,
                    "quantity":
                        "0.500",
                    "condition":
                        "good",
                },
                {
                    "invoice_item_id":
                        item_id,
                    "quantity":
                        "0.500",
                    "condition":
                        "good",
                },
            ],
        },
    )

    assert response.status_code == 422

    assert (
        "same invoice item"
        in response.text.lower()
    )


@pytest.mark.asyncio
async def test_rejected_return_cannot_create_credit_note(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_confirmed_sale(
        client,
        admin_headers,
        db_session,
        suffix="403",
    )

    sales_return = await create_return(
        client,
        admin_headers,
        invoice_id=
            fixture["invoice"]["id"],
        invoice_item_id=
            fixture["invoice_item"]["id"],
    )

    await inspect_return(
        client,
        admin_headers,
        sales_return["id"],
    )

    rejection = await client.post(
        (
            f"{RETURNS_URL}/"
            f"{sales_return['id']}/approval"
        ),
        headers=admin_headers,
        json={
            "approved":
                False,
            "resolution":
                "rejected",
            "approval_notes":
                "Return rejected after inspection",
            "refund_amount":
                "0.00",
        },
    )

    assert rejection.status_code == 200
    assert rejection.json()["status"] == "rejected"

    credit_response = await client.post(
        CREDIT_URL,
        headers=admin_headers,
        json={
            "return_id":
                sales_return["id"],
        },
    )

    assert credit_response.status_code == 409


@pytest.mark.asyncio
async def test_credit_note_post_creates_customer_overpayment(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="404",
        fully_paid=True,
    )

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

    quantity_before = await stock_quantity(
        db_session,
        product_id=product_id,
        warehouse_id=returned_warehouse_id,
    )

    credit_note = (
        await create_approve_post_credit_note(
            client,
            admin_headers,
            return_id=
                fixture["return"]["id"],
        )
    )

    assert dec(
        credit_note["amount"]
    ) == Decimal("1200.00")

    assert dec(
        credit_note["invoice_paid_amount"]
    ) == Decimal("2400.00")

    assert dec(
        credit_note["refundable_overpayment"]
    ) == Decimal("1200.00")

    invoice_response = await client.get(
        (
            "/api/v1/sales/invoices/"
            f"{fixture['invoice']['id']}"
        ),
        headers=admin_headers,
    )

    assert invoice_response.status_code == 200

    invoice = invoice_response.json()

    assert dec(
        invoice["credited_amount"]
    ) == Decimal("1200.00")

    assert dec(
        invoice["paid_amount"]
    ) == Decimal("2400.00")

    quantity_after = await stock_quantity(
        db_session,
        product_id=product_id,
        warehouse_id=returned_warehouse_id,
    )

    assert quantity_after == (
        quantity_before
        + Decimal("1.000")
    )


@pytest.mark.asyncio
async def test_refund_create_post_and_reverse(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="405",
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

    create_response = await client.post(
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
                "REF-405",
            "notes":
                "Integration cash refund",
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    refund = create_response.json()

    assert refund["refund_number"].startswith(
        "RF-"
    )
    assert refund["status"] == "pending"
    assert refund["is_reversed"] is False

    post_response = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund['id']}/post"
        ),
        headers=admin_headers,
    )

    assert post_response.status_code == 200

    posted = post_response.json()

    assert posted["status"] == "posted"
    assert posted["posted_at"] is not None

    invoice_response = await client.get(
        (
            "/api/v1/sales/invoices/"
            f"{fixture['invoice']['id']}"
        ),
        headers=admin_headers,
    )

    invoice = invoice_response.json()

    assert dec(
        invoice["paid_amount"]
    ) == Decimal("1200.00")

    return_response = await client.get(
        (
            f"{RETURNS_URL}/"
            f"{fixture['return']['id']}"
        ),
        headers=admin_headers,
    )

    assert return_response.status_code == 200
    assert (
        return_response.json()["status"]
        == "completed"
    )

    reverse_response = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Refund reversal integration test",
        },
    )

    assert reverse_response.status_code == 200

    reversed_refund = reverse_response.json()

    assert reversed_refund["status"] == "reversed"
    assert reversed_refund["is_reversed"] is True

    invoice_response = await client.get(
        (
            "/api/v1/sales/invoices/"
            f"{fixture['invoice']['id']}"
        ),
        headers=admin_headers,
    )

    invoice = invoice_response.json()

    assert dec(
        invoice["paid_amount"]
    ) == Decimal("2400.00")

    return_response = await client.get(
        (
            f"{RETURNS_URL}/"
            f"{fixture['return']['id']}"
        ),
        headers=admin_headers,
    )

    assert (
        return_response.json()["status"]
        == "processing"
    )


@pytest.mark.asyncio
async def test_active_refund_blocks_credit_note_reversal(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="406",
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
        f"{CREDIT_URL}/refunds",
        headers=admin_headers,
        json={
            "credit_note_id":
                credit_note["id"],
            "amount":
                "1200.00",
            "refund_method":
                "cash",
        },
    )

    assert refund_response.status_code == 201

    refund_id = refund_response.json()["id"]

    posted = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund_id}/post"
        ),
        headers=admin_headers,
    )

    assert posted.status_code == 200

    blocked = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Should be blocked by active refund",
        },
    )

    assert blocked.status_code == 409

    assert (
        "active refunds"
        in blocked.json()["detail"].lower()
    )


@pytest.mark.asyncio
async def test_credit_note_reversal_restores_invoice_and_stock(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="407",
        fully_paid=True,
    )

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

    credit_note = (
        await create_approve_post_credit_note(
            client,
            admin_headers,
            return_id=
                fixture["return"]["id"],
        )
    )

    credited_stock_quantity = (
        await stock_quantity(
            db_session,
            product_id=product_id,
            warehouse_id=returned_warehouse_id,
        )
    )

    assert credited_stock_quantity >= (
        Decimal("1.000")
    )

    reverse_response = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Credit note integration reversal",
        },
    )

    assert reverse_response.status_code == 200, (
        reverse_response.text
    )

    reversed_credit = reverse_response.json()

    assert reversed_credit["status"] == "reversed"
    assert reversed_credit["is_reversed"] is True

    invoice_response = await client.get(
        (
            "/api/v1/sales/invoices/"
            f"{fixture['invoice']['id']}"
        ),
        headers=admin_headers,
    )

    invoice = invoice_response.json()

    assert dec(
        invoice["credited_amount"]
    ) == Decimal("0.00")

    reversed_stock_quantity = (
        await stock_quantity(
            db_session,
            product_id=product_id,
            warehouse_id=returned_warehouse_id,
        )
    )

    assert reversed_stock_quantity == (
        credited_stock_quantity
        - Decimal("1.000")
    )

    return_response = await client.get(
        (
            f"{RETURNS_URL}/"
            f"{fixture['return']['id']}"
        ),
        headers=admin_headers,
    )

    assert return_response.status_code == 200

    assert (
        return_response.json()["status"]
        == "approved"
    )


@pytest.mark.asyncio
async def test_refund_overpayment_guard(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="408",
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

    response = await client.post(
        f"{CREDIT_URL}/refunds",
        headers=admin_headers,
        json={
            "credit_note_id":
                credit_note["id"],
            "amount":
                "1200.01",
            "refund_method":
                "cash",
        },
    )

    assert response.status_code == 422

    assert (
        "refund amount exceeds"
        in response.json()["detail"].lower()
    )


@pytest.mark.asyncio
async def test_return_credit_refund_audit_chain(
    client,
    admin_headers,
    db_session,
):
    fixture = await prepare_refund_return(
        client,
        admin_headers,
        db_session,
        suffix="409",
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
        f"{CREDIT_URL}/refunds",
        headers=admin_headers,
        json={
            "credit_note_id":
                credit_note["id"],
            "amount":
                "1200.00",
            "refund_method":
                "cash",
        },
    )

    assert refund_response.status_code == 201

    refund_id = refund_response.json()["id"]

    post_refund_response = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund_id}/post"
        ),
        headers=admin_headers,
    )

    assert post_refund_response.status_code == 200

    reverse_refund_response = await client.post(
        (
            f"{CREDIT_URL}/refunds/"
            f"{refund_id}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Audit refund reversal",
        },
    )

    assert reverse_refund_response.status_code == 200

    reverse_credit_response = await client.post(
        (
            f"{CREDIT_URL}/"
            f"{credit_note['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Audit credit note reversal",
        },
    )

    assert reverse_credit_response.status_code == 200

    audit_rows = (
        await db_session.execute(
            select(AuditLog)
        )
    ).scalars().all()

    actions = {
        row.action
        for row in audit_rows
    }

    expected = {
        "return.created",
        "return.inspected",
        "return.approved",
        "credit_note.created",
        "credit_note.approved",
        "credit_note.posted",
        "refund.created",
        "refund.posted",
        "refund.reversed",
        "credit_note.reversed",
    }

    missing = expected - actions

    assert not missing, (
        f"Missing audit actions: {sorted(missing)}"
    )
