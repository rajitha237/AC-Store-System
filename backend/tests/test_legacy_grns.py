from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import (
    func,
    select,
)

from app.models import (
    LegacyGoodsReceipt,
    LegacyGoodsReceiptItem,
    ProductSerialNumber,
    PurchaseOrder,
    StockItem,
    StockMovement,
    SupplierInvoice,
    SupplierPayment,
)


BASE_URL = "/api/v1/legacy-grns"


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
                f"Legacy GRN Supplier {suffix}",

            "contact_person":
                f"Legacy Contact {suffix}",

            "phone":
                f"070{numeric:07d}",

            "email":
                (
                    f"legacy-grn-{suffix}"
                    "@example.com"
                ),

            "address_line_1":
                "Legacy History Address",

            "city":
                "Kekirawa",

            "credit_limit":
                "0.00",

            "payment_terms_days":
                0,

            "notes":
                "Legacy GRN API test supplier",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_legacy_fixture(
    client,
    admin_headers,
    db_session,
    *,
    suffix: str,
):
    supplier = await create_supplier(
        client,
        admin_headers,
        suffix=suffix,
    )

    numeric = int(suffix)

    receipt = LegacyGoodsReceipt(
        company_id=1,
        supplier_id=supplier["id"],

        legacy_grn_id=(
            f"OLD-{suffix}"
        ),

        legacy_internal_id=(
            900000 + numeric
        ),

        legacy_supplier_id=(
            1000 + numeric
        ),

        legacy_grn_number=(
            f"00{suffix}"
        ),

        reference_invoice_number=(
            f"LEGACY-INV-{suffix}"
        ),

        receipt_date=date(
            2025,
            8,
            21,
        ),

        total_amount=Decimal(
            "2500.00"
        ),

        discount_amount=Decimal(
            "0.00"
        ),

        net_total=Decimal(
            "2500.00"
        ),

        paid_amount=Decimal(
            "1000.00"
        ),

        outstanding_amount=Decimal(
            "1500.00"
        ),

        legacy_status="historical",

        source_system=(
            "legacy_ac_store"
        ),

        source_payload={
            "source":
                "test",
            "legacy_suffix":
                suffix,
        },
    )

    db_session.add(
        receipt
    )

    await db_session.flush()

    item = LegacyGoodsReceiptItem(
        legacy_goods_receipt_id=(
            receipt.id
        ),

        product_id=None,

        legacy_item_id=(
            800000 + numeric
        ),

        legacy_created_grn_id=(
            receipt.legacy_internal_id
        ),

        legacy_product_code=(
            f"OLD-CODE-{suffix}"
        ),

        legacy_product_name=(
            f"Legacy Product {suffix}"
        ),

        quantity=Decimal(
            "2.000"
        ),

        unit_cost=Decimal(
            "1250.00"
        ),

        retail_price=Decimal(
            "1500.00"
        ),

        wholesale_price=Decimal(
            "1400.00"
        ),

        discount_amount=Decimal(
            "0.00"
        ),

        line_total=Decimal(
            "2500.00"
        ),

        temporary_stock=Decimal(
            "2.000"
        ),

        expiry_date=None,
        expiry_status=None,

        legacy_type="stock",

        serial_numbers_json=[
            f"LEGACY-SN-{suffix}-A",
            f"LEGACY-SN-{suffix}-B",
        ],

        imeis_json=[],

        source_payload={
            "source":
                "test_item",
        },
    )

    db_session.add(
        item
    )

    await db_session.commit()

    return {
        "supplier":
            supplier,
        "receipt":
            receipt,
        "item":
            item,
    }


async def count_rows(
    db_session,
    model,
) -> int:
    result = await db_session.execute(
        select(
            func.count()
        )
        .select_from(
            model
        )
    )

    return int(
        result.scalar_one()
    )


@pytest.mark.asyncio
async def test_legacy_grn_list_and_detail(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_legacy_fixture(
        client,
        admin_headers,
        db_session,
        suffix="701",
    )

    receipt = fixture[
        "receipt"
    ]

    supplier = fixture[
        "supplier"
    ]

    list_response = await client.get(
        BASE_URL,
        headers=admin_headers,
    )

    assert (
        list_response.status_code
        == 200
    ), list_response.text

    data = list_response.json()

    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 1

    row = data["items"][0]

    assert (
        row["legacy_grn_number"]
        == "00701"
    )

    assert (
        row["supplier_id"]
        == supplier["id"]
    )

    assert (
        row["supplier_name"]
        == supplier["company_name"]
    )

    assert row["item_count"] == 1

    assert (
        Decimal(
            row["net_total"]
        )
        == Decimal(
            "2500.00"
        )
    )

    detail = await client.get(
        (
            f"{BASE_URL}/"
            f"{receipt.id}"
        ),
        headers=admin_headers,
    )

    assert (
        detail.status_code
        == 200
    ), detail.text

    body = detail.json()

    assert (
        body["legacy_grn_number"]
        == "00701"
    )

    assert (
        body[
            "reference_invoice_number"
        ]
        == "LEGACY-INV-701"
    )

    assert len(
        body["items"]
    ) == 1

    item = body["items"][0]

    assert (
        item["legacy_product_code"]
        == "OLD-CODE-701"
    )

    assert item["product_id"] is None

    assert (
        item["serial_numbers_json"]
        == [
            "LEGACY-SN-701-A",
            "LEGACY-SN-701-B",
        ]
    )


@pytest.mark.asyncio
async def test_legacy_grn_search_and_supplier_filter(
    client,
    admin_headers,
    db_session,
):
    first = await create_legacy_fixture(
        client,
        admin_headers,
        db_session,
        suffix="702",
    )

    await create_legacy_fixture(
        client,
        admin_headers,
        db_session,
        suffix="703",
    )

    response = await client.get(
        BASE_URL,
        headers=admin_headers,
        params={
            "search":
                "LEGACY-INV-702",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1

    assert (
        data["items"][0][
            "legacy_grn_number"
        ]
        == "00702"
    )

    filtered = await client.get(
        BASE_URL,
        headers=admin_headers,
        params={
            "supplier_id":
                first[
                    "supplier"
                ]["id"],
        },
    )

    assert filtered.status_code == 200

    filtered_data = filtered.json()

    assert filtered_data["total"] == 1

    assert (
        filtered_data["items"][0][
            "supplier_id"
        ]
        == first[
            "supplier"
        ]["id"]
    )


@pytest.mark.asyncio
async def test_legacy_grn_missing_detail_returns_404(
    client,
    admin_headers,
):
    response = await client.get(
        f"{BASE_URL}/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_legacy_grn_requires_authentication(
    client,
):
    list_response = await client.get(
        BASE_URL
    )

    detail_response = await client.get(
        f"{BASE_URL}/1"
    )

    assert (
        list_response.status_code
        == 401
    )

    assert (
        detail_response.status_code
        == 401
    )


@pytest.mark.asyncio
async def test_legacy_grn_api_has_no_write_methods(
    client,
    admin_headers,
):
    for method in (
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ):
        response = await client.request(
            method,
            BASE_URL,
            headers=admin_headers,
            json={},
        )

        assert response.status_code == 405


@pytest.mark.asyncio
async def test_legacy_grn_reads_do_not_mutate_operational_data(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_legacy_fixture(
        client,
        admin_headers,
        db_session,
        suffix="704",
    )

    protected_models = [
        StockItem,
        StockMovement,
        ProductSerialNumber,
        PurchaseOrder,
        SupplierInvoice,
        SupplierPayment,
    ]

    before = {
        model.__tablename__:
            await count_rows(
                db_session,
                model,
            )
        for model
        in protected_models
    }

    list_response = await client.get(
        BASE_URL,
        headers=admin_headers,
    )

    assert list_response.status_code == 200

    detail_response = await client.get(
        (
            f"{BASE_URL}/"
            f"{fixture['receipt'].id}"
        ),
        headers=admin_headers,
    )

    assert (
        detail_response.status_code
        == 200
    )

    db_session.expire_all()

    after = {
        model.__tablename__:
            await count_rows(
                db_session,
                model,
            )
        for model
        in protected_models
    }

    assert after == before

    assert (
        after[
            "stock_movements"
        ]
        == before[
            "stock_movements"
        ]
    )

    assert (
        after[
            "product_serial_numbers"
        ]
        == before[
            "product_serial_numbers"
        ]
    )

    assert (
        after[
            "purchase_orders"
        ]
        == before[
            "purchase_orders"
        ]
    )

    assert (
        after[
            "supplier_invoices"
        ]
        == before[
            "supplier_invoices"
        ]
    )

    assert (
        after[
            "supplier_payments"
        ]
        == before[
            "supplier_payments"
        ]
    )
