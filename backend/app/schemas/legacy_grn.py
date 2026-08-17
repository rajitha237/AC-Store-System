from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class LegacyGoodsReceiptItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    legacy_goods_receipt_id: int

    product_id: int | None

    legacy_item_id: int
    legacy_created_grn_id: int | None

    legacy_product_code: str | None
    legacy_product_name: str | None

    quantity: Decimal
    unit_cost: Decimal

    retail_price: Decimal | None
    wholesale_price: Decimal | None

    discount_amount: Decimal
    line_total: Decimal

    temporary_stock: Decimal | None

    expiry_date: date | None
    expiry_status: str | None

    legacy_type: str | None

    serial_numbers_json: Any | None
    imeis_json: Any | None

    source_payload: dict[str, Any] | None

    created_at: datetime


class LegacyGoodsReceiptListItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    supplier_id: int
    supplier_name: str | None = None

    legacy_internal_id: int
    legacy_supplier_id: int

    legacy_grn_id: str | None
    legacy_grn_number: str

    reference_invoice_number: str | None

    receipt_date: date

    total_amount: Decimal
    discount_amount: Decimal
    net_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal

    legacy_status: str | None
    source_system: str

    item_count: int

    created_at: datetime


class LegacyGoodsReceiptResponse(
    LegacyGoodsReceiptListItem
):
    items: list[
        LegacyGoodsReceiptItemResponse
    ]

    source_payload: (
        dict[str, Any]
        | None
    )


class LegacyGoodsReceiptListResponse(BaseModel):
    items: list[
        LegacyGoodsReceiptListItem
    ]

    total: int
    page: int
    page_size: int
    total_pages: int
