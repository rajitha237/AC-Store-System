from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    ProductSerialNumber,
    PurchaseOrder,
    StockItem,
    StockMovement,
)
from tests.test_inventory import (
    create_product,
    get_warehouse,
)
from tests.test_purchase_orders import (
    create_po_fixture,
    create_supplier,
)


BASE_URL = "/api/v1/purchase-orders"


def dec(value) -> Decimal:
    return Decimal(str(value))


async def approve_po(
    client,
    admin_headers,
    po_id: int,
):
    response = await client.post(
        f"{BASE_URL}/{po_id}/approve",
        headers=admin_headers,
    )

    assert response.status_code == 200, (
        response.text
    )

    return response.json()


@pytest.mark.asyncio
async def test_partial_non_serialized_grn(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="951",
        quantity="2.000",
        unit_cost="1000.00",
        discount="0.00",
        tax="0.00",
    )

    po = fixture["purchase_order"]

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    po_item = po["items"][0]

    response = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "delivery_note_number":
                "DN-951",

            "items": [
                {
                    "purchase_order_item_id":
                        po_item["id"],

                    "quantity":
                        "1.000",
                }
            ],
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    data = response.json()

    assert data["grn_number"].startswith(
        "GRN-"
    )

    assert (
        data["po_status"]
        == "partially_received"
    )

    detail = await client.get(
        f"{BASE_URL}/{po['id']}",
        headers=admin_headers,
    )

    assert detail.status_code == 200

    po_after = detail.json()

    assert (
        po_after["status"]
        == "partially_received"
    )

    assert dec(
        po_after["items"][0][
            "received_quantity"
        ]
    ) == Decimal("1.000")

    stock_result = await db_session.execute(
        select(StockItem).where(
            StockItem.product_id
            == fixture["product"]["id"],
            StockItem.warehouse_id
            == fixture["warehouse"]["id"],
        )
    )

    stock = stock_result.scalar_one()

    assert dec(
        stock.quantity_on_hand
    ) == Decimal("1.000")

    assert dec(
        stock.average_cost
    ) == Decimal("1000.00")

    movement_result = (
        await db_session.execute(
            select(StockMovement).where(
                StockMovement.reference_id
                == data["grn_number"]
            )
        )
    )

    movements = (
        movement_result.scalars().all()
    )

    assert len(movements) == 1

    assert (
        movements[0].movement_type
        == "purchase_receipt"
    )


@pytest.mark.asyncio
async def test_second_grn_completes_po(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="952",
        quantity="2.000",
        unit_cost="750.00",
        discount="0.00",
        tax="0.00",
    )

    po = fixture["purchase_order"]

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    item_id = po["items"][0]["id"]

    first = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        item_id,

                    "quantity":
                        "1.000",
                }
            ]
        },
    )

    assert first.status_code == 201

    second = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        item_id,

                    "quantity":
                        "1.000",
                }
            ]
        },
    )

    assert second.status_code == 201, (
        second.text
    )

    assert (
        second.json()["po_status"]
        == "received"
    )

    detail = await client.get(
        f"{BASE_URL}/{po['id']}",
        headers=admin_headers,
    )

    po_after = detail.json()

    assert po_after["status"] == "received"

    assert dec(
        po_after["items"][0][
            "received_quantity"
        ]
    ) == Decimal("2.000")


@pytest.mark.asyncio
async def test_over_receipt_is_rejected_atomically(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="953",
        quantity="1.000",
        unit_cost="500.00",
        discount="0.00",
        tax="0.00",
    )

    po = fixture["purchase_order"]

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "2.000",
                }
            ]
        },
    )

    assert response.status_code == 409

    stock_result = await db_session.execute(
        select(StockItem).where(
            StockItem.product_id
            == fixture["product"]["id"],
            StockItem.warehouse_id
            == fixture["warehouse"]["id"],
        )
    )

    assert (
        stock_result.scalar_one_or_none()
        is None
    )


@pytest.mark.asyncio
async def test_draft_po_cannot_be_received(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="954",
    )

    po = fixture["purchase_order"]

    response = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "1.000",
                }
            ]
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_serialized_grn_creates_serials_and_movements(
    client,
    admin_headers,
    db_session,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix="955",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="955",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    po_response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json={
            "supplier_id":
                supplier["id"],

            "warehouse_id":
                warehouse["id"],

            "items": [
                {
                    "product_id":
                        product["id"],

                    "quantity":
                        "2.000",

                    "unit_cost":
                        "1200.00",

                    "discount_amount":
                        "0.00",

                    "tax_amount":
                        "0.00",
                }
            ],
        },
    )

    assert po_response.status_code == 201, (
        po_response.text
    )

    po = po_response.json()

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    receive = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "2.000",

                    "serials": [
                        {
                            "serial_number":
                                "PO-GRN-955-A",
                        },
                        {
                            "serial_number":
                                "PO-GRN-955-B",

                            "secondary_serial_number":
                                "PO-GRN-955-B2",
                        },
                    ],
                }
            ],
        },
    )

    assert receive.status_code == 201, (
        receive.text
    )

    data = receive.json()

    assert data["po_status"] == "received"

    assert (
        len(
            data["items"][0]["serials"]
        )
        == 2
    )

    serial_result = await db_session.execute(
        select(ProductSerialNumber)
        .where(
            ProductSerialNumber.product_id
            == product["id"]
        )
    )

    serials = (
        serial_result.scalars().all()
    )

    assert len(serials) == 2

    assert {
        serial.status
        for serial in serials
    } == {"available"}

    assert {
        serial.warehouse_id
        for serial in serials
    } == {warehouse["id"]}

    movement_result = await db_session.execute(
        select(StockMovement).where(
            StockMovement.reference_id
            == data["grn_number"]
        )
    )

    movements = (
        movement_result.scalars().all()
    )

    assert len(movements) == 2

    assert all(
        movement.movement_type
        == "purchase_receipt"
        for movement in movements
    )

    assert all(
        movement.serial_number_id
        is not None
        for movement in movements
    )


@pytest.mark.asyncio
async def test_serial_count_must_match_quantity(
    client,
    admin_headers,
    db_session,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix="956",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="956",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    po_response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json={
            "supplier_id":
                supplier["id"],

            "warehouse_id":
                warehouse["id"],

            "items": [
                {
                    "product_id":
                        product["id"],

                    "quantity":
                        "2.000",

                    "unit_cost":
                        "500.00",
                }
            ],
        },
    )

    assert po_response.status_code == 201

    po = po_response.json()

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "2.000",

                    "serials": [
                        {
                            "serial_number":
                                "PO-GRN-956-A",
                        }
                    ],
                }
            ]
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_serial_receipt_rolls_back(
    client,
    admin_headers,
    db_session,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix="957",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="957",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    po_response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json={
            "supplier_id":
                supplier["id"],

            "warehouse_id":
                warehouse["id"],

            "items": [
                {
                    "product_id":
                        product["id"],

                    "quantity":
                        "2.000",

                    "unit_cost":
                        "650.00",
                }
            ],
        },
    )

    assert po_response.status_code == 201

    po = po_response.json()

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "2.000",

                    "serials": [
                        {
                            "serial_number":
                                "PO-GRN-957-X",
                        },
                        {
                            "serial_number":
                                "PO-GRN-957-X",
                        },
                    ],
                }
            ]
        },
    )

    assert response.status_code == 422

    serial_result = await db_session.execute(
        select(ProductSerialNumber).where(
            ProductSerialNumber.product_id
            == product["id"]
        )
    )

    assert (
        serial_result.scalars().all()
        == []
    )


@pytest.mark.asyncio
async def test_goods_receipt_list_and_detail(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="958",
        quantity="1.000",
        unit_cost="999.00",
        discount="0.00",
        tax="0.00",
    )

    po = fixture["purchase_order"]

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    receive = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],

                    "quantity":
                        "1.000",
                }
            ]
        },
    )

    assert receive.status_code == 201

    grn = receive.json()

    list_response = await client.get(
        f"{BASE_URL}/goods-receipts",
        headers=admin_headers,
        params={
            "purchase_order_id":
                po["id"],
        },
    )

    assert list_response.status_code == 200

    data = list_response.json()

    assert data["total"] == 1

    detail = await client.get(
        (
            f"{BASE_URL}/goods-receipts/"
            f"{grn['id']}"
        ),
        headers=admin_headers,
    )

    assert detail.status_code == 200

    assert (
        detail.json()["grn_number"]
        == grn["grn_number"]
    )


@pytest.mark.asyncio
async def test_receive_endpoint_requires_authentication(
    client,
):
    response = await client.post(
        f"{BASE_URL}/1/receive",
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        1,

                    "quantity":
                        "1.000",
                }
            ]
        },
    )

    assert response.status_code == 401
