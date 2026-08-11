from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    AuditLog,
    PurchaseOrder,
    PurchaseOrderItem,
)
from tests.test_inventory import (
    create_product,
    get_warehouse,
)


BASE_URL = "/api/v1/purchase-orders"


def dec(value) -> Decimal:
    return Decimal(str(value))


async def create_supplier(
    client,
    admin_headers,
    *,
    suffix: str,
):
    numeric = int(suffix)

    response = await client.post(
        "/api/v1/suppliers",
        headers=admin_headers,
        json={
            "company_name":
                f"PO Supplier {suffix}",

            "contact_person":
                f"PO Contact {suffix}",

            "phone":
                f"071{numeric:07d}",

            "email":
                (
                    f"po-supplier-"
                    f"{suffix}@example.com"
                ),

            "address_line_1":
                "Purchasing Test Address",

            "city":
                "Colombo",

            "credit_limit":
                "500000.00",

            "payment_terms_days":
                30,

            "notes":
                "Purchase order integration supplier",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_po_fixture(
    client,
    admin_headers,
    db_session,
    *,
    suffix: str,
    quantity="2.000",
    unit_cost="1000.00",
    discount="100.00",
    tax="50.00",
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix=suffix,
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    payload = {
        "supplier_id":
            supplier["id"],

        "warehouse_id":
            warehouse["id"],

        "order_date":
            "2026-08-11",

        "expected_date":
            "2026-08-20",

        "notes":
            f"PO fixture {suffix}",

        "items": [
            {
                "product_id":
                    product["id"],

                "quantity":
                    quantity,

                "unit_cost":
                    unit_cost,

                "discount_amount":
                    discount,

                "tax_amount":
                    tax,

                "notes":
                    "Primary purchase item",
            }
        ],
    }

    response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, (
        response.text
    )

    return {
        "purchase_order":
            response.json(),

        "supplier":
            supplier,

        "product":
            product,

        "warehouse":
            warehouse,

        "payload":
            payload,
    }


@pytest.mark.asyncio
async def test_purchase_order_create_and_totals(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="901",
    )

    po = fixture[
        "purchase_order"
    ]

    assert po["status"] == "draft"

    assert po[
        "purchase_order_number"
    ].startswith("PO-")

    assert dec(
        po["subtotal"]
    ) == Decimal("2000.00")

    assert dec(
        po["discount_amount"]
    ) == Decimal("100.00")

    assert dec(
        po["tax_amount"]
    ) == Decimal("50.00")

    assert dec(
        po["grand_total"]
    ) == Decimal("1950.00")

    assert len(po["items"]) == 1

    assert dec(
        po["items"][0]["quantity"]
    ) == Decimal("2.000")

    assert dec(
        po["items"][0][
            "received_quantity"
        ]
    ) == Decimal("0.000")


@pytest.mark.asyncio
async def test_purchase_order_list_and_detail(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="902",
    )

    po = fixture[
        "purchase_order"
    ]

    list_response = await client.get(
        BASE_URL,
        headers=admin_headers,
        params={
            "search":
                po[
                    "purchase_order_number"
                ],

            "order_status":
                "draft",
        },
    )

    assert (
        list_response.status_code
        == 200
    ), list_response.text

    data = list_response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    detail_response = await client.get(
        f"{BASE_URL}/{po['id']}",
        headers=admin_headers,
    )

    assert (
        detail_response.status_code
        == 200
    )

    detail = detail_response.json()

    assert detail["id"] == po["id"]
    assert len(detail["items"]) == 1


@pytest.mark.asyncio
async def test_draft_purchase_order_can_be_updated(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="903",
    )

    po = fixture[
        "purchase_order"
    ]

    product = fixture["product"]

    response = await client.patch(
        f"{BASE_URL}/{po['id']}",
        headers=admin_headers,
        json={
            "expected_date":
                "2026-08-25",

            "notes":
                "Updated PO draft",

            "items": [
                {
                    "product_id":
                        product["id"],

                    "quantity":
                        "3.000",

                    "unit_cost":
                        "900.00",

                    "discount_amount":
                        "0.00",

                    "tax_amount":
                        "270.00",
                }
            ],
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    assert (
        data["notes"]
        == "Updated PO draft"
    )

    assert dec(
        data["subtotal"]
    ) == Decimal("2700.00")

    assert dec(
        data["grand_total"]
    ) == Decimal("2970.00")


@pytest.mark.asyncio
async def test_purchase_order_approve_and_lock(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="904",
    )

    po = fixture[
        "purchase_order"
    ]

    approve = await client.post(
        (
            f"{BASE_URL}/"
            f"{po['id']}/approve"
        ),
        headers=admin_headers,
    )

    assert approve.status_code == 200, (
        approve.text
    )

    approved = approve.json()

    assert (
        approved["status"]
        == "approved"
    )

    assert (
        approved["approved_by_id"]
        is not None
    )

    assert (
        approved["approved_at"]
        is not None
    )

    edit = await client.patch(
        f"{BASE_URL}/{po['id']}",
        headers=admin_headers,
        json={
            "notes":
                "This edit must fail",
        },
    )

    assert edit.status_code == 409

    second_approve = await client.post(
        (
            f"{BASE_URL}/"
            f"{po['id']}/approve"
        ),
        headers=admin_headers,
    )

    assert (
        second_approve.status_code
        == 409
    )


@pytest.mark.asyncio
async def test_purchase_order_cancel(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="905",
    )

    po = fixture[
        "purchase_order"
    ]

    response = await client.post(
        (
            f"{BASE_URL}/"
            f"{po['id']}/cancel"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Supplier quotation withdrawn",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    assert (
        data["status"]
        == "cancelled"
    )

    assert (
        data["cancellation_reason"]
        == "Supplier quotation withdrawn"
    )


@pytest.mark.asyncio
async def test_duplicate_product_line_rejected(
    client,
    admin_headers,
    db_session,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix="906",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="906",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    line = {
        "product_id":
            product["id"],

        "quantity":
            "1.000",

        "unit_cost":
            "1000.00",

        "discount_amount":
            "0.00",

        "tax_amount":
            "0.00",
    }

    response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json={
            "supplier_id":
                supplier["id"],

            "warehouse_id":
                warehouse["id"],

            "items":
                [
                    line,
                    {
                        **line,
                        "quantity":
                            "2.000",
                    },
                ],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_expected_date_rejected(
    client,
    admin_headers,
    db_session,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix="907",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="907",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json={
            "supplier_id":
                supplier["id"],

            "warehouse_id":
                warehouse["id"],

            "order_date":
                "2026-08-20",

            "expected_date":
                "2026-08-10",

            "items": [
                {
                    "product_id":
                        product["id"],

                    "quantity":
                        "1.000",

                    "unit_cost":
                        "1000.00",
                }
            ],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_purchase_order_audit_actions_created(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="908",
    )

    po = fixture[
        "purchase_order"
    ]

    approve = await client.post(
        (
            f"{BASE_URL}/"
            f"{po['id']}/approve"
        ),
        headers=admin_headers,
    )

    assert approve.status_code == 200

    result = await db_session.execute(
        select(AuditLog)
        .where(
            AuditLog.module
            == "purchasing"
        )
        .order_by(AuditLog.id)
    )

    actions = {
        row.action
        for row
        in result.scalars().all()
    }

    assert (
        "purchasing.purchase_order_created"
        in actions
    )

    assert (
        "purchasing.purchase_order_approved"
        in actions
    )


@pytest.mark.asyncio
async def test_purchase_order_persistence_models(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="909",
    )

    po_id = fixture[
        "purchase_order"
    ]["id"]

    result = await db_session.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id
        )
    )

    po = result.scalar_one()

    assert po.status == "draft"

    item_result = await db_session.execute(
        select(PurchaseOrderItem).where(
            PurchaseOrderItem
            .purchase_order_id
            == po_id
        )
    )

    items = item_result.scalars().all()

    assert len(items) == 1


@pytest.mark.asyncio
async def test_purchase_orders_require_authentication(
    client,
):
    response = await client.get(
        BASE_URL
    )

    assert response.status_code == 401
