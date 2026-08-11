from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    AuditLog,
    Brand,
    Customer,
    Product,
    ProductSerialNumber,
    StockItem,
    StockMovement,
    UnitOfMeasure,
    Warehouse,
)


async def get_warehouse(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/inventory/warehouses",
        headers=admin_headers,
    )

    assert response.status_code == 200

    warehouses = response.json()

    assert warehouses

    main = next(
        (
            item
            for item in warehouses
            if item["code"] == "MAIN"
        ),
        warehouses[0],
    )

    return main


async def get_unit_id(
    db_session,
):
    result = await db_session.execute(
        select(UnitOfMeasure)
        .where(
            UnitOfMeasure.is_active.is_(True)
        )
        .order_by(UnitOfMeasure.id)
    )

    unit = result.scalars().first()

    assert unit is not None

    return unit.id


async def create_category(
    client,
    admin_headers,
    code,
):
    response = await client.post(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        json={
            "code": code,
            "name": f"{code} Category",
            "description": "Inventory test category",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()


async def create_brand(
    client,
    admin_headers,
    code,
):
    response = await client.post(
        "/api/v1/catalog/brands",
        headers=admin_headers,
        json={
            "code": code,
            "name": f"{code} Brand",
            "description": "Inventory test brand",
            "is_active": True,
        },
    )

    assert response.status_code == 201

    return response.json()


async def create_product(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
    serialized,
    reorder_level="2.000",
    warranty_months=12,
):
    category = await create_category(
        client,
        admin_headers,
        f"INV-CAT-{suffix}",
    )

    brand = await create_brand(
        client,
        admin_headers,
        f"INV-BRAND-{suffix}",
    )

    unit_id = await get_unit_id(
        db_session
    )

    payload = {
        "barcode":
            f"BAR-{suffix}",
        "category_id":
            category["id"],
        "brand_id":
            brand["id"],
        "unit_id":
            unit_id,
        "name":
            f"Inventory Product {suffix}",
        "model_number":
            f"MODEL-{suffix}",
        "description":
            "Inventory integration test product",
        "product_type":
            "equipment",
        "track_serial_numbers":
            serialized,
        "purchase_cost":
            "100.00",
        "selling_price":
            "150.00",
        "minimum_selling_price":
            "140.00",
        "warranty_months":
            warranty_months,
        "reorder_level":
            reorder_level,
        "reorder_quantity":
            "5.000",
        "technical_notes":
            "Inventory integration pytest product",
    }

    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, (
        "PRODUCT CREATE FAILED: "
        f"{response.status_code} "
        f"{response.text}"
    )

    return response.json()


async def create_customer(
    client,
    admin_headers,
    suffix,
):
    response = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "customer_type":
                "cash",
            "full_name":
                f"Inventory Customer {suffix}",
            "business_name":
                f"Inventory Business {suffix}",
            "nic_number":
                f"200000000{int(suffix):03d}",
            "primary_phone":
                f"0778{int(suffix):06d}",
            "sms_phone":
                f"0778{int(suffix):06d}",
            "email":
                f"inventory{suffix}@example.com",
            "address_line_1":
                "Inventory Test Address",
            "city":
                "Colombo",
            "credit_status":
                "restricted",
            "credit_limit":
                "0.00",
            "sms_allowed":
                True,
            "notes":
                "Inventory integration test customer",
        },
    )

    assert response.status_code == 201, (
        "CUSTOMER CREATE FAILED: "
        f"{response.status_code} "
        f"{response.text}"
    )

    return response.json()


async def receive_non_serialized(
    client,
    admin_headers,
    *,
    product_id,
    warehouse_id,
    quantity,
    unit_cost,
    reference_id,
):
    return await client.post(
        "/api/v1/inventory/receive/non-serialized",
        headers=admin_headers,
        json={
            "product_id":
                product_id,
            "warehouse_id":
                warehouse_id,
            "quantity":
                quantity,
            "unit_cost":
                unit_cost,
            "reference_type":
                "opening_balance",
            "reference_id":
                reference_id,
            "notes":
                "Inventory integration test receipt",
        },
    )


@pytest.mark.asyncio
async def test_inventory_warehouses_seeded(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/inventory/warehouses",
        headers=admin_headers,
    )

    assert response.status_code == 200

    warehouses = response.json()

    codes = {
        item["code"]
        for item in warehouses
    }

    assert {
        "MAIN",
        "SERVICE",
        "FAULTY",
        "RETURNED",
        "SUP-CLAIM",
    }.issubset(codes)


@pytest.mark.asyncio
async def test_non_serialized_receive_and_balance(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="101",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    response = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="100.00",
        reference_id="OPEN-101",
    )

    assert response.status_code == 201

    data = response.json()

    assert Decimal(
        str(data["quantity_received"])
    ) == Decimal("10.000")

    assert Decimal(
        str(data["quantity_on_hand"])
    ) == Decimal("10.000")

    assert Decimal(
        str(data["average_cost"])
    ) == Decimal("100.00")

    balance_response = await client.get(
        "/api/v1/inventory/balances",
        headers=admin_headers,
        params={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
        },
    )

    assert balance_response.status_code == 200

    balances = balance_response.json()

    assert len(balances) == 1

    assert Decimal(
        str(
            balances[0][
                "quantity_on_hand"
            ]
        )
    ) == Decimal("10.000")


@pytest.mark.asyncio
async def test_non_serialized_weighted_average_cost(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="102",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    first = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="100.00",
        reference_id="OPEN-102-A",
    )

    assert first.status_code == 201

    second = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="200.00",
        reference_id="OPEN-102-B",
    )

    assert second.status_code == 201

    data = second.json()

    assert Decimal(
        str(data["quantity_on_hand"])
    ) == Decimal("20.000")

    assert Decimal(
        str(data["average_cost"])
    ) == Decimal("150.00")


@pytest.mark.asyncio
async def test_non_serialized_issue(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="103",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="125.00",
        reference_id="OPEN-103",
    )

    assert received.status_code == 201

    response = await client.post(
        "/api/v1/inventory/issue/non-serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "quantity":
                "3.000",
            "issue_type":
                "sale",
            "reference_type":
                "sale",
            "reference_id":
                "SALE-103",
            "notes":
                "Inventory integration test issue",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert Decimal(
        str(data["quantity_issued"])
    ) == Decimal("3.000")

    assert Decimal(
        str(data["quantity_on_hand"])
    ) == Decimal("7.000")

    assert Decimal(
        str(
            data["movement"]["quantity"]
        )
    ) == Decimal("-3.000")


@pytest.mark.asyncio
async def test_non_serialized_insufficient_stock_rejected(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="104",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="2.000",
        unit_cost="100.00",
        reference_id="OPEN-104",
    )

    assert received.status_code == 201

    response = await client.post(
        "/api/v1/inventory/issue/non-serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "quantity":
                "3.000",
            "issue_type":
                "sale",
            "reference_type":
                "sale",
            "reference_id":
                "SALE-104",
        },
    )

    assert response.status_code == 409

    assert (
        "Insufficient available stock"
        in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_serialized_receive_and_lookup(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="105",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    response = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "unit_cost":
                "500.00",
            "reference_type":
                "opening_balance",
            "reference_id":
                "OPEN-105",
            "notes":
                "Serialized inventory test",
            "serials": [
                {
                    "serial_number":
                        "SN-INV-105-A",
                },
                {
                    "serial_number":
                        "SN-INV-105-B",
                },
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["quantity_received"] == 2

    assert Decimal(
        str(data["quantity_on_hand"])
    ) == Decimal("2.000")

    assert len(data["serials"]) == 2

    serial_id = data["serials"][0]["id"]

    detail_response = await client.get(
        (
            "/api/v1/inventory/"
            f"serial-numbers/{serial_id}"
        ),
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert (
        detail["serial_number"]
        == "SN-INV-105-A"
    )

    assert detail["status"] == "available"

    list_response = await client.get(
        "/api/v1/inventory/serial-numbers",
        headers=admin_headers,
        params={
            "search":
                "SN-INV-105",
            "product_id":
                product["id"],
        },
    )

    assert list_response.status_code == 200

    serials = list_response.json()

    assert len(serials) == 2


@pytest.mark.asyncio
async def test_duplicate_serial_number_rejected(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="106",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    payload = {
        "product_id":
            product["id"],
        "warehouse_id":
            warehouse["id"],
        "unit_cost":
            "500.00",
        "reference_type":
            "opening_balance",
        "reference_id":
            "OPEN-106",
        "serials": [
            {
                "serial_number":
                    "SN-DUP-106",
            },
        ],
    }

    first = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201

    second = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json={
            **payload,
            "reference_id":
                "OPEN-106-B",
        },
    )

    assert second.status_code == 409

    detail = second.json()["detail"]

    assert (
        "serial number already exists"
        in detail.lower()
    )
    assert "SN-DUP-106" in detail


@pytest.mark.asyncio
async def test_serialized_issue_to_customer(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="107",
        serialized=True,
        warranty_months=12,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    customer = await create_customer(
        client,
        admin_headers,
        "107",
    )

    receive_response = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "unit_cost":
                "600.00",
            "reference_type":
                "opening_balance",
            "reference_id":
                "OPEN-107",
            "serials": [
                {
                    "serial_number":
                        "SN-ISSUE-107",
                },
            ],
        },
    )

    assert receive_response.status_code == 201

    serial = receive_response.json()[
        "serials"
    ][0]

    response = await client.post(
        "/api/v1/inventory/issue/serialized",
        headers=admin_headers,
        json={
            "serial_number_id":
                serial["id"],
            "customer_id":
                customer["id"],
            "issue_type":
                "sale",
            "reference_type":
                "sale",
            "reference_id":
                "SALE-107",
            "warranty_start_date":
                "2026-08-09",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["customer_id"] == customer["id"]

    assert Decimal(
        str(data["quantity_on_hand"])
    ) == Decimal("0.000")

    assert data["serial"]["status"] == "sold"

    assert (
        data["serial"]["current_customer_id"]
        == customer["id"]
    )

    assert (
        data["serial"]["warehouse_id"]
        is None
    )

    assert (
        data["serial"]["warranty_start_date"]
        == "2026-08-09"
    )

    assert (
        data["serial"]["warranty_end_date"]
        is not None
    )


@pytest.mark.asyncio
async def test_serialized_item_cannot_be_issued_twice(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="108",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    customer = await create_customer(
        client,
        admin_headers,
        "108",
    )

    receive_response = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "unit_cost":
                "700.00",
            "reference_type":
                "opening_balance",
            "reference_id":
                "OPEN-108",
            "serials": [
                {
                    "serial_number":
                        "SN-DOUBLE-108",
                },
            ],
        },
    )

    assert receive_response.status_code == 201

    serial_id = receive_response.json()[
        "serials"
    ][0]["id"]

    payload = {
        "serial_number_id":
            serial_id,
        "customer_id":
            customer["id"],
        "issue_type":
            "sale",
        "reference_type":
            "sale",
        "reference_id":
            "SALE-108",
    }

    first = await client.post(
        "/api/v1/inventory/issue/serialized",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 200

    second = await client.post(
        "/api/v1/inventory/issue/serialized",
        headers=admin_headers,
        json={
            **payload,
            "reference_id":
                "SALE-108-B",
        },
    )

    assert second.status_code == 409

    assert (
        "Only an available serial number"
        in second.json()["detail"]
    )


@pytest.mark.asyncio
async def test_tracking_mode_mismatch_rejected(
    client,
    admin_headers,
    db_session,
):
    non_serialized_product = (
        await create_product(
            client,
            admin_headers,
            db_session,
            suffix="109",
            serialized=False,
        )
    )

    serialized_product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="110",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    serialized_receive = await client.post(
        "/api/v1/inventory/receive/serialized",
        headers=admin_headers,
        json={
            "product_id":
                non_serialized_product["id"],
            "warehouse_id":
                warehouse["id"],
            "unit_cost":
                "100.00",
            "serials": [
                {
                    "serial_number":
                        "SN-WRONG-109",
                },
            ],
        },
    )

    assert serialized_receive.status_code == 409

    non_serialized_receive = (
        await receive_non_serialized(
            client,
            admin_headers,
            product_id=
                serialized_product["id"],
            warehouse_id=
                warehouse["id"],
            quantity="1.000",
            unit_cost="100.00",
            reference_id="OPEN-110",
        )
    )

    assert (
        non_serialized_receive.status_code
        == 409
    )


@pytest.mark.asyncio
async def test_inventory_movements_and_audit_created(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="111",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="5.000",
        unit_cost="100.00",
        reference_id="OPEN-111",
    )

    assert received.status_code == 201

    issued = await client.post(
        "/api/v1/inventory/issue/non-serialized",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "quantity":
                "2.000",
            "issue_type":
                "sale",
            "reference_type":
                "sale",
            "reference_id":
                "SALE-111",
        },
    )

    assert issued.status_code == 200

    movements_response = await client.get(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        params={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
        },
    )

    assert movements_response.status_code == 200

    movement_payload = (
        movements_response.json()
    )

    if isinstance(
        movement_payload,
        dict,
    ):
        movements = (
            movement_payload.get("items")
            or movement_payload.get("data")
            or []
        )
    else:
        movements = movement_payload

    assert len(movements) >= 2

    movement_result = await db_session.execute(
        select(StockMovement)
        .where(
            StockMovement.product_id
            == product["id"]
        )
    )

    db_movements = (
        movement_result.scalars().all()
    )

    assert len(db_movements) == 2

    audit_result = await db_session.execute(
        select(AuditLog)
        .where(
            AuditLog.module == "inventory"
        )
        .where(
            AuditLog.action.in_(
                [
                    (
                        "inventory."
                        "stock_received_non_serialized"
                    ),
                    (
                        "inventory."
                        "stock_issued_non_serialized"
                    ),
                ]
            )
        )
    )

    audits = audit_result.scalars().all()

    actions = {
        audit.action
        for audit in audits
    }

    assert (
        "inventory."
        "stock_received_non_serialized"
        in actions
    )

    assert (
        "inventory."
        "stock_issued_non_serialized"
        in actions
    )


@pytest.mark.asyncio
async def test_low_stock_filter(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="112",
        serialized=False,
        reorder_level="5.000",
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="3.000",
        unit_cost="100.00",
        reference_id="OPEN-112",
    )

    assert received.status_code == 201

    response = await client.get(
        "/api/v1/inventory/balances",
        headers=admin_headers,
        params={
            "product_id":
                product["id"],
            "low_stock_only":
                "true",
        },
    )

    assert response.status_code == 200

    balances = response.json()

    assert len(balances) == 1

    assert balances[0]["is_low_stock"] is True


@pytest.mark.asyncio
async def test_inventory_requires_authentication(
    client,
):
    endpoints = [
        (
            "GET",
            "/api/v1/inventory/warehouses",
            None,
        ),
        (
            "GET",
            "/api/v1/inventory/balances",
            None,
        ),
        (
            "GET",
            "/api/v1/inventory/movements",
            None,
        ),
        (
            "GET",
            "/api/v1/inventory/serial-numbers",
            None,
        ),
    ]

    for method, path, payload in endpoints:
        response = await client.request(
            method,
            path,
            json=payload,
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_phase4a_adjustment_increase(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="P4A201",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="100.00",
        reference_id="P4A-OPEN-201",
    )

    assert received.status_code == 201

    response = await client.post(
        "/api/v1/inventory/adjust",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "direction":
                "increase",
            "quantity":
                "2.000",
            "unit_cost":
                "200.00",
            "reference_id":
                "P4A-INC-201",
            "reason":
                "Physical count surplus",
            "notes":
                "Phase 4A test",
        },
    )

    assert (
        response.status_code
        == 200
    ), response.text

    data = response.json()

    assert Decimal(
        str(
            data[
                "quantity_on_hand"
            ]
        )
    ) == Decimal("12.000")

    assert Decimal(
        str(
            data[
                "quantity_available"
            ]
        )
    ) == Decimal("12.000")

    assert (
        data["movement"][
            "movement_type"
        ]
        == "adjustment_increase"
    )

    assert Decimal(
        str(
            data["movement"][
                "quantity"
            ]
        )
    ) == Decimal("2.000")


@pytest.mark.asyncio
async def test_phase4a_adjustment_decrease(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="P4A202",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="100.00",
        reference_id="P4A-OPEN-202",
    )

    assert received.status_code == 201

    response = await client.post(
        "/api/v1/inventory/adjust",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "direction":
                "decrease",
            "quantity":
                "3.000",
            "reference_id":
                "P4A-DEC-202",
            "reason":
                "Physical count shortage",
        },
    )

    assert (
        response.status_code
        == 200
    ), response.text

    data = response.json()

    assert Decimal(
        str(
            data[
                "quantity_on_hand"
            ]
        )
    ) == Decimal("7.000")

    assert (
        data["movement"][
            "movement_type"
        ]
        == "adjustment_decrease"
    )

    assert Decimal(
        str(
            data["movement"][
                "quantity"
            ]
        )
    ) == Decimal("-3.000")


@pytest.mark.asyncio
async def test_phase4a_adjustment_blocks_excess_decrease(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="P4A203",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="2.000",
        unit_cost="100.00",
        reference_id="P4A-OPEN-203",
    )

    assert received.status_code == 201

    response = await client.post(
        "/api/v1/inventory/adjust",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "direction":
                "decrease",
            "quantity":
                "3.000",
            "reference_id":
                "P4A-BLOCK-203",
            "reason":
                "Invalid stock reduction",
        },
    )

    assert (
        response.status_code
        == 409
    ), response.text

    assert (
        "Insufficient available stock"
        in response.json()[
            "detail"
        ]
    )


@pytest.mark.asyncio
async def test_phase4a_serialized_adjustment_fails_closed(
    client,
    admin_headers,
    db_session,
):
    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="P4A204",
        serialized=True,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    response = await client.post(
        "/api/v1/inventory/adjust",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "direction":
                "increase",
            "quantity":
                "1.000",
            "unit_cost":
                "100.00",
            "reference_id":
                "P4A-SERIAL-204",
            "reason":
                "Serialized safety check",
        },
    )

    assert (
        response.status_code
        == 409
    ), response.text

    assert (
        "Serialized products"
        in response.json()[
            "detail"
        ]
    )
