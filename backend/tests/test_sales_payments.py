from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    AuditLog,
    Branch,
    Customer,
    CustomerPayment,
    ProductSerialNumber,
    SalesInvoice,
    StockItem,
    StockMovement,
    UnitOfMeasure,
)
from app.schemas.sales import (
    SalesInvoiceCreate,
)


def dec(value) -> Decimal:
    return Decimal(str(value))


async def get_main_branch_id(
    db_session,
):
    branch = (
        await db_session.execute(
            select(Branch)
            .where(
                Branch.is_active.is_(True)
            )
            .order_by(Branch.id)
        )
    ).scalars().first()

    assert branch is not None

    return branch.id


async def get_unit_id(
    db_session,
):
    unit = (
        await db_session.execute(
            select(UnitOfMeasure)
            .where(
                UnitOfMeasure.is_active.is_(True)
            )
            .order_by(UnitOfMeasure.id)
        )
    ).scalars().first()

    assert unit is not None

    return unit.id


async def create_customer(
    client,
    admin_headers,
    *,
    suffix,
):
    response = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "customer_type":
                "credit",
            "full_name":
                f"Sales Customer {suffix}",
            "business_name":
                f"Sales Business {suffix}",
            "nic_number":
                f"200100000{int(suffix):03d}",
            "primary_phone":
                f"0767{int(suffix):06d}",
            "sms_phone":
                f"0767{int(suffix):06d}",
            "email":
                f"sales{suffix}@example.com",
            "address_line_1":
                "Sales Test Address",
            "city":
                "Colombo",
            "credit_status":
                "allowed",
            "credit_limit":
                "1000000.00",
            "sms_allowed":
                True,
            "notes":
                "Sales payment integration customer",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_category(
    client,
    admin_headers,
    *,
    suffix,
):
    response = await client.post(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        json={
            "code":
                f"SALE-CAT-{suffix}",
            "name":
                f"Sales Category {suffix}",
            "description":
                "Sales integration category",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_brand(
    client,
    admin_headers,
    *,
    suffix,
):
    response = await client.post(
        "/api/v1/catalog/brands",
        headers=admin_headers,
        json={
            "code":
                f"SALE-BRAND-{suffix}",
            "name":
                f"Sales Brand {suffix}",
            "description":
                "Sales integration brand",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_non_serialized_product(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
    selling_price="1200.00",
):
    category = await create_category(
        client,
        admin_headers,
        suffix=suffix,
    )

    brand = await create_brand(
        client,
        admin_headers,
        suffix=suffix,
    )

    unit_id = await get_unit_id(
        db_session
    )

    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "barcode":
                f"SALE-BAR-{suffix}",
            "category_id":
                category["id"],
            "brand_id":
                brand["id"],
            "unit_id":
                unit_id,
            "name":
                f"Sales Product {suffix}",
            "model_number":
                f"SALE-MODEL-{suffix}",
            "description":
                "Sales integration product",
            "product_type":
                "accessory",
            "track_serial_numbers":
                False,
            "purchase_cost":
                "750.00",
            "selling_price":
                selling_price,
            "minimum_selling_price":
                "1000.00",
            "warranty_months":
                0,
            "reorder_level":
                "2.000",
            "reorder_quantity":
                "10.000",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def get_main_warehouse(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/inventory/warehouses",
        headers=admin_headers,
    )

    assert response.status_code == 200

    warehouses = response.json()

    warehouse = next(
        item
        for item in warehouses
        if item["code"] == "MAIN"
    )

    return warehouse


async def receive_stock(
    client,
    admin_headers,
    *,
    product_id,
    warehouse_id,
    suffix,
    quantity="20.000",
):
    response = await client.post(
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
                "750.00",
            "reference_type":
                "opening_balance",
            "reference_id":
                f"SALE-OPEN-{suffix}",
            "notes":
                "Sales integration opening stock",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_sales_fixture(
    client,
    admin_headers,
    db_session,
    *,
    suffix,
    quantity="2.000",
    unit_price="1200.00",
    invoice_discount="0.00",
    tax_amount="0.00",
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix=suffix,
    )

    product = await create_non_serialized_product(
        client,
        admin_headers,
        db_session,
        suffix=suffix,
        selling_price=unit_price,
    )

    warehouse = await get_main_warehouse(
        client,
        admin_headers,
    )

    await receive_stock(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        suffix=suffix,
    )

    branch_id = await get_main_branch_id(
        db_session
    )

    item = {
        "product_id":
            product["id"],
        "warehouse_id":
            warehouse["id"],
        "serial_number_id":
            None,
        "quantity":
            quantity,
        "unit_price":
            unit_price,
        "discount_amount":
            "0.00",
        "description":
            f"Sales integration item {suffix}",
    }

    payload = {
        "branch_id":
            branch_id,
        "customer_id":
            customer["id"],
        "invoice_discount_amount":
            invoice_discount,
        "tax_amount":
            tax_amount,
        "notes":
            f"Sales integration invoice {suffix}",
        "items": [
            item
        ],
    }

    #
    # Remove optional keys only if the current
    # SalesInvoiceCreate contract does not expose them.
    #
    allowed = set(
        SalesInvoiceCreate.model_fields
    )

    payload = {
        key: value
        for key, value in payload.items()
        if key in allowed
    }

    response = await client.post(
        "/api/v1/sales/invoices",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, (
        "INVOICE CREATE FAILED: "
        f"{response.status_code} "
        f"{response.text}"
    )

    invoice = response.json()

    return {
        "customer":
            customer,
        "product":
            product,
        "warehouse":
            warehouse,
        "invoice":
            invoice,
    }


async def confirm_invoice(
    client,
    admin_headers,
    invoice_id,
    *,
    initial_payment=None,
):
    payload = {}

    if initial_payment is not None:
        payload["initial_payment"] = (
            initial_payment
        )

    return await client.post(
        (
            "/api/v1/sales/invoices/"
            f"{invoice_id}/confirm"
        ),
        headers=admin_headers,
        json=payload,
    )


@pytest.mark.asyncio
async def test_sales_draft_invoice_lifecycle(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="201",
    )

    invoice = fixture["invoice"]

    assert invoice["id"] >= 1
    assert invoice["invoice_number"].startswith(
        "INV-"
    )
    assert invoice["invoice_status"] == "draft"
    assert invoice["payment_status"] == "unpaid"

    assert dec(
        invoice["grand_total"]
    ) == Decimal("2400.00")

    assert dec(
        invoice["paid_amount"]
    ) == Decimal("0.00")

    assert dec(
        invoice["balance_amount"]
    ) == Decimal("2400.00")

    detail_response = await client.get(
        (
            "/api/v1/sales/invoices/"
            f"{invoice['id']}"
        ),
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["id"] == invoice["id"]
    assert len(detail["items"]) == 1
    assert detail["payments"] == []

    list_response = await client.get(
        "/api/v1/sales/invoices",
        headers=admin_headers,
        params={
            "search":
                invoice["invoice_number"],
            "invoice_status":
                "draft",
        },
    )

    assert list_response.status_code == 200

    listing = list_response.json()

    assert listing["total"] == 1

    assert (
        listing["items"][0]["id"]
        == invoice["id"]
    )


@pytest.mark.asyncio
async def test_confirm_invoice_deducts_stock_and_adds_customer_balance(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="202",
        quantity="3.000",
    )

    invoice = fixture["invoice"]
    product = fixture["product"]
    warehouse = fixture["warehouse"]
    customer = fixture["customer"]

    response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
    )

    assert response.status_code == 200, (
        response.text
    )

    confirmed = response.json()

    assert (
        confirmed["invoice_status"]
        == "confirmed"
    )
    assert (
        confirmed["payment_status"]
        == "unpaid"
    )

    assert dec(
        confirmed["grand_total"]
    ) == Decimal("3600.00")

    assert dec(
        confirmed["balance_amount"]
    ) == Decimal("3600.00")

    stock = (
        await db_session.execute(
            select(StockItem)
            .where(
                StockItem.product_id
                == product["id"],
                StockItem.warehouse_id
                == warehouse["id"],
            )
        )
    ).scalar_one()

    assert dec(
        stock.quantity_on_hand
    ) == Decimal("17.000")

    customer_row = await db_session.get(
        Customer,
        customer["id"],
    )

    assert dec(
        customer_row.current_balance
    ) == Decimal("3600.00")


@pytest.mark.asyncio
async def test_confirm_invoice_below_stock_average_cost_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="209",
        quantity="2.000",
        unit_price="1200.00",
    )

    invoice = fixture["invoice"]
    product = fixture["product"]
    warehouse = fixture["warehouse"]

    stock = (
        await db_session.execute(
            select(StockItem)
            .where(
                StockItem.product_id
                == product["id"],
                StockItem.warehouse_id
                == warehouse["id"],
            )
        )
    ).scalar_one()

    quantity_before = dec(
        stock.quantity_on_hand
    )

    stock.average_cost = Decimal(
        "1300.00"
    )

    # Commit the test setup so the separate API request
    # session can read the updated average cost.
    # Without this, SQLite keeps the fixture transaction
    # write-locked and the API session sees stale stock data.
    await db_session.commit()

    response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
    )

    assert response.status_code == 409, (
        response.text
    )

    assert (
        response.json()["detail"]
        == (
            f"{product['product_code']}: "
            "sale price 1200.00 is below "
            "stock average cost 1300.00"
        )
    )

    await db_session.refresh(stock)

    assert dec(
        stock.quantity_on_hand
    ) == quantity_before

    invoice_row = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )

    assert invoice_row is not None
    assert invoice_row.invoice_status == "draft"

    customer_row = await db_session.get(
        Customer,
        fixture["customer"]["id"],
    )

    assert customer_row is not None
    assert dec(
        customer_row.current_balance
    ) == Decimal("0.00")




@pytest.mark.asyncio
async def test_confirm_serialized_invoice_below_stock_average_cost_rejected(
    client,
    admin_headers,
    db_session,
):
    suffix = "210"

    customer = await create_customer(
        client,
        admin_headers,
        suffix=suffix,
    )

    category = await create_category(
        client,
        admin_headers,
        suffix=suffix,
    )

    brand = await create_brand(
        client,
        admin_headers,
        suffix=suffix,
    )

    unit_id = await get_unit_id(
        db_session
    )

    product_response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "barcode":
                f"SALE-SERIAL-BAR-{suffix}",
            "category_id":
                category["id"],
            "brand_id":
                brand["id"],
            "unit_id":
                unit_id,
            "name":
                f"Serialized Sales Product {suffix}",
            "model_number":
                f"SALE-SERIAL-MODEL-{suffix}",
            "description":
                "Serialized below-cost regression product",
            "product_type":
                "equipment",
            "track_serial_numbers":
                True,
            "purchase_cost":
                "200000.00",
            "selling_price":
                "200000.00",
            "minimum_selling_price":
                "190000.00",
            "warranty_months":
                12,
            "reorder_level":
                "1.000",
            "reorder_quantity":
                "1.000",
        },
    )

    assert product_response.status_code == 201, (
        product_response.text
    )

    product = product_response.json()

    warehouse = await get_main_warehouse(
        client,
        admin_headers,
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
                "200000.00",
            "reference_type":
                "opening_balance",
            "reference_id":
                f"SALE-SERIAL-OPEN-{suffix}",
            "notes":
                "Serialized below-cost regression stock",
            "serials": [
                {
                    "serial_number":
                        f"SALE-SERIAL-{suffix}",
                },
            ],
        },
    )

    assert receive_response.status_code == 201, (
        receive_response.text
    )

    received = receive_response.json()

    assert received["quantity_received"] == 1

    serial_id = received["serials"][0]["id"]

    branch_id = await get_main_branch_id(
        db_session
    )

    invoice_response = await client.post(
        "/api/v1/sales/invoices",
        headers=admin_headers,
        json={
            "branch_id":
                branch_id,
            "customer_id":
                customer["id"],
            "invoice_discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
            "notes":
                "Serialized below-cost regression invoice",
            "items": [
                {
                    "product_id":
                        product["id"],
                    "warehouse_id":
                        warehouse["id"],
                    "serial_number_id":
                        serial_id,
                    "quantity":
                        "1.000",
                    "unit_price":
                        "190000.00",
                    "discount_amount":
                        "0.00",
                    "description":
                        "Serialized below-cost sale attempt",
                },
            ],
        },
    )

    assert invoice_response.status_code == 201, (
        invoice_response.text
    )

    invoice = invoice_response.json()

    stock = (
        await db_session.execute(
            select(StockItem)
            .where(
                StockItem.product_id
                == product["id"],
                StockItem.warehouse_id
                == warehouse["id"],
            )
        )
    ).scalar_one()

    serial = await db_session.get(
        ProductSerialNumber,
        serial_id,
    )

    assert serial is not None

    quantity_before = dec(
        stock.quantity_on_hand
    )

    warehouse_before = (
        serial.warehouse_id
    )

    customer_before = (
        serial.current_customer_id
    )

    status_before = serial.status
    sold_at_before = serial.sold_at

    await db_session.commit()

    response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
    )

    assert response.status_code == 409, (
        response.text
    )

    assert (
        response.json()["detail"]
        == (
            f"{product['product_code']}: "
            "sale price 190000.00 is below "
            "stock average cost 200000.00"
        )
    )

    await db_session.refresh(stock)
    await db_session.refresh(serial)

    assert dec(
        stock.quantity_on_hand
    ) == quantity_before

    assert (
        serial.status
        == status_before
        == "available"
    )

    assert (
        serial.warehouse_id
        == warehouse_before
        == warehouse["id"]
    )

    assert (
        serial.current_customer_id
        == customer_before
        is None
    )

    assert (
        serial.sold_at
        == sold_at_before
        is None
    )

    invoice_row = await db_session.get(
        SalesInvoice,
        invoice["id"],
    )

    assert invoice_row is not None
    assert invoice_row.invoice_status == "draft"

    customer_row = await db_session.get(
        Customer,
        customer["id"],
    )

    assert customer_row is not None

    assert dec(
        customer_row.current_balance
    ) == Decimal("0.00")

    movement_count = (
        await db_session.execute(
            select(StockMovement)
            .where(
                StockMovement.product_id
                == product["id"],
                StockMovement.reference_type
                == "sales_invoice",
                StockMovement.reference_id
                == invoice["invoice_number"],
            )
        )
    ).scalars().all()

    assert movement_count == []



@pytest.mark.asyncio
async def test_confirm_invoice_twice_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="203",
    )

    invoice_id = fixture["invoice"]["id"]

    first = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert first.status_code == 200

    second = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert second.status_code == 409

    assert (
        second.json()["detail"]
        == "Only a draft invoice can be confirmed"
    )


@pytest.mark.asyncio
async def test_payment_on_draft_invoice_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="204",
    )

    response = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                fixture["invoice"]["id"],
            "amount":
                "500.00",
            "payment_method":
                "cash",
        },
    )

    assert response.status_code == 409

    assert (
        response.json()["detail"]
        == (
            "Payments can only be received "
            "for confirmed invoices"
        )
    )


@pytest.mark.asyncio
async def test_partial_then_full_payment_flow(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="205",
    )

    invoice_id = fixture["invoice"]["id"]
    customer_id = fixture["customer"]["id"]

    confirmed_response = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirmed_response.status_code == 200

    first = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "1000.00",
            "payment_method":
                "cash",
            "reference_number":
                "PAY-205-A",
        },
    )

    assert first.status_code == 201, first.text

    partial = first.json()

    assert (
        partial["payment_status"]
        == "partial"
    )
    assert dec(
        partial["paid_amount"]
    ) == Decimal("1000.00")
    assert dec(
        partial["balance_amount"]
    ) == Decimal("1400.00")
    assert dec(
        partial["customer_balance"]
    ) == Decimal("1400.00")

    second = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "1400.00",
            "payment_method":
                "bank_transfer",
            "reference_number":
                "PAY-205-B",
        },
    )

    assert second.status_code == 201, (
        second.text
    )

    paid = second.json()

    assert paid["payment_status"] == "paid"
    assert dec(
        paid["paid_amount"]
    ) == Decimal("2400.00")
    assert dec(
        paid["balance_amount"]
    ) == Decimal("0.00")
    assert dec(
        paid["customer_balance"]
    ) == Decimal("0.00")

    invoice_row = await db_session.get(
        SalesInvoice,
        invoice_id,
    )

    assert invoice_row.payment_status == "paid"

    customer_row = await db_session.get(
        Customer,
        customer_id,
    )

    assert dec(
        customer_row.current_balance
    ) == Decimal("0.00")


@pytest.mark.asyncio
async def test_overpayment_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="206",
    )

    invoice_id = fixture["invoice"]["id"]

    confirmed = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirmed.status_code == 200

    response = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "2400.01",
            "payment_method":
                "cash",
        },
    )

    assert response.status_code == 422

    assert (
        "Payment amount cannot exceed "
        in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_payment_reversal_restores_balances(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="207",
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
                "1000.00",
            "payment_method":
                "cash",
            "reference_number":
                "REV-207",
        },
    )

    assert payment_response.status_code == 201

    payment_id = payment_response.json()[
        "payment"
    ]["id"]

    reverse_response = await client.post(
        (
            "/api/v1/payments/"
            f"{payment_id}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Integration test reversal",
        },
    )

    assert reverse_response.status_code == 200, (
        reverse_response.text
    )

    reversed_data = reverse_response.json()

    assert (
        reversed_data["payment"]["is_reversed"]
        is True
    )
    assert (
        reversed_data["payment_status"]
        == "unpaid"
    )
    assert dec(
        reversed_data["paid_amount"]
    ) == Decimal("0.00")
    assert dec(
        reversed_data["balance_amount"]
    ) == Decimal("2400.00")
    assert dec(
        reversed_data["customer_balance"]
    ) == Decimal("2400.00")

    second_reverse = await client.post(
        (
            "/api/v1/payments/"
            f"{payment_id}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Second reversal attempt",
        },
    )

    assert second_reverse.status_code == 409

    assert (
        second_reverse.json()["detail"]
        == "This payment has already been reversed"
    )


@pytest.mark.asyncio
async def test_payment_list_and_detail_filters(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="208",
    )

    invoice_id = fixture["invoice"]["id"]
    customer_id = fixture["customer"]["id"]

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
                "500.00",
            "payment_method":
                "card",
            "reference_number":
                "FILTER-208",
        },
    )

    assert payment_response.status_code == 201

    payment = payment_response.json()["payment"]

    detail_response = await client.get(
        f"/api/v1/payments/{payment['id']}",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200

    detail = detail_response.json()

    assert detail["id"] == payment["id"]
    assert detail["invoice_id"] == invoice_id
    assert detail["customer_id"] == customer_id

    list_response = await client.get(
        "/api/v1/payments",
        headers=admin_headers,
        params={
            "invoice_id":
                invoice_id,
            "customer_id":
                customer_id,
            "is_reversed":
                "false",
            "search":
                "FILTER-208",
        },
    )

    assert list_response.status_code == 200

    listing = list_response.json()

    assert listing["total"] == 1
    assert (
        listing["items"][0]["id"]
        == payment["id"]
    )


@pytest.mark.asyncio
async def test_confirm_with_initial_payment(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="209",
    )

    response = await confirm_invoice(
        client,
        admin_headers,
        fixture["invoice"]["id"],
        initial_payment={
            "amount":
                "400.00",
            "payment_method":
                "cash",
            "reference_number":
                "INITIAL-209",
            "notes":
                "Initial invoice payment",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    invoice = response.json()

    assert (
        invoice["invoice_status"]
        == "confirmed"
    )
    assert (
        invoice["payment_status"]
        == "partial"
    )

    assert dec(
        invoice["paid_amount"]
    ) == Decimal("400.00")

    assert dec(
        invoice["balance_amount"]
    ) == Decimal("2000.00")

    assert len(invoice["payments"]) == 1

    assert dec(
        invoice["payments"][0]["amount"]
    ) == Decimal("400.00")


@pytest.mark.asyncio
async def test_sales_and_payment_audit_logs_created(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="210",
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
                "500.00",
            "payment_method":
                "cash",
        },
    )

    assert payment_response.status_code == 201

    payment_id = payment_response.json()[
        "payment"
    ]["id"]

    reverse_response = await client.post(
        (
            "/api/v1/payments/"
            f"{payment_id}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Audit integration reversal",
        },
    )

    assert reverse_response.status_code == 200

    audit_rows = (
        await db_session.execute(
            select(AuditLog)
            .where(
                AuditLog.action.in_(
                    [
                        "sales.invoice_draft_created",
                        "sales.invoice_confirmed",
                        "payment.received",
                        "payment.reversed",
                    ]
                )
            )
        )
    ).scalars().all()

    actions = {
        row.action
        for row in audit_rows
    }

    assert (
        "sales.invoice_draft_created"
        in actions
    )
    assert (
        "sales.invoice_confirmed"
        in actions
    )
    assert "payment.received" in actions
    assert "payment.reversed" in actions


@pytest.mark.asyncio
async def test_fully_paid_invoice_rejects_extra_payment(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="211",
    )

    invoice_id = fixture["invoice"]["id"]

    confirmed = await confirm_invoice(
        client,
        admin_headers,
        invoice_id,
    )

    assert confirmed.status_code == 200

    payment = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "2400.00",
            "payment_method":
                "cash",
        },
    )

    assert payment.status_code == 201
    assert (
        payment.json()["payment_status"]
        == "paid"
    )

    extra = await client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "invoice_id":
                invoice_id,
            "amount":
                "1.00",
            "payment_method":
                "cash",
        },
    )

    assert extra.status_code == 409

    assert (
        extra.json()["detail"]
        == "This invoice is already fully paid"
    )
