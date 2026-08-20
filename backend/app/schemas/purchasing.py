from __future__ import annotations

from datetime import (
    date,
    datetime,
)
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.purchasing import (
    PurchaseOrderStatus,
)


class PurchaseOrderItemInput(BaseModel):
    product_id: int = Field(
        ge=1,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
    )

    unit_cost: Decimal = Field(
        ge=Decimal("0.00"),
    )

    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
    )


class PurchaseOrderCreate(BaseModel):
    supplier_id: int = Field(
        ge=1,
    )

    warehouse_id: int = Field(
        ge=1,
    )

    order_date: date = Field(
        default_factory=date.today,
    )

    expected_date: date | None = None

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    items: list[
        PurchaseOrderItemInput
    ] = Field(
        min_length=1,
        max_length=500,
    )


class PurchaseOrderUpdate(BaseModel):
    supplier_id: int | None = Field(
        default=None,
        ge=1,
    )

    warehouse_id: int | None = Field(
        default=None,
        ge=1,
    )

    order_date: date | None = None

    expected_date: date | None = None

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    items: list[
        PurchaseOrderItemInput
    ] | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )


class PurchaseOrderCancelRequest(BaseModel):
    reason: str = Field(
        min_length=3,
        max_length=250,
    )


class PurchaseOrderItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    product_id: int

    product_code: str | None = None
    product_name: str

    quantity: Decimal
    received_quantity: Decimal

    unit_cost: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal

    notes: str | None = None


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    purchase_order_number: str

    company_id: int
    branch_id: int

    supplier_id: int
    supplier_code: str | None = None
    supplier_name: str

    warehouse_id: int
    warehouse_code: str
    warehouse_name: str

    status: PurchaseOrderStatus

    order_date: date
    expected_date: date | None

    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal

    notes: str | None

    approved_by_id: int | None
    approved_at: datetime | None

    cancelled_by_id: int | None
    cancelled_at: datetime | None
    cancellation_reason: str | None

    created_by_id: int
    updated_by_id: int | None

    created_at: datetime
    updated_at: datetime


class PurchaseOrderDetailResponse(
    PurchaseOrderResponse
):
    items: list[
        PurchaseOrderItemResponse
    ]


class PurchaseOrderListResponse(BaseModel):
    items: list[
        PurchaseOrderResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int


class GoodsReceiptSerialInput(BaseModel):
    serial_number: str = Field(
        min_length=1,
        max_length=150,
    )

    secondary_serial_number: str | None = Field(
        default=None,
        max_length=150,
    )


class GoodsReceiptItemInput(BaseModel):
    purchase_order_item_id: int = Field(
        ge=1,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
    )

    serials: list[
        GoodsReceiptSerialInput
    ] = Field(
        default_factory=list,
        max_length=1000,
    )


class GoodsReceiptCreate(BaseModel):
    delivery_note_number: str | None = Field(
            default=None,
            max_length=100,
        )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    items: list[
        GoodsReceiptItemInput
    ] = Field(
        min_length=1,
        max_length=500,
    )


class GoodsReceiptSerialResponse(BaseModel):
    id: int
    product_serial_number_id: int

    serial_number: str
    secondary_serial_number: str | None


class GoodsReceiptItemResponse(BaseModel):
    id: int

    purchase_order_item_id: int
    product_id: int

    product_code: str
    product_name: str

    quantity_received: Decimal
    unit_cost: Decimal

    serials: list[
        GoodsReceiptSerialResponse
    ]


class GoodsReceiptResponse(BaseModel):
    id: int
    grn_number: str

    purchase_order_id: int
    purchase_order_number: str

    company_id: int
    branch_id: int

    supplier_id: int
    supplier_name: str

    warehouse_id: int
    warehouse_code: str
    warehouse_name: str

    received_at: datetime

    delivery_note_number: str | None

    notes: str | None

    received_by_id: int

    po_status: PurchaseOrderStatus

    items: list[
        GoodsReceiptItemResponse
    ]

    created_at: datetime


class GoodsReceiptListResponse(BaseModel):
    items: list[
        GoodsReceiptResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int


class SupplierInvoiceCreate(BaseModel):
    supplier_id: int = Field(
        ge=1,
    )

    purchase_order_id: int | None = Field(
        default=None,
        ge=1,
    )

    goods_receipt_id: int | None = Field(
        default=None,
        ge=1,
    )

    supplier_invoice_number: str = Field(
        min_length=1,
        max_length=100,
    )

    invoice_date: datetime | None = None

    due_date: date | None = None

    subtotal: Decimal = Field(
        ge=Decimal("0.00"),
    )

    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class SupplierInvoiceReverseRequest(
    BaseModel
):
    reason: str = Field(
        min_length=3,
        max_length=500,
    )


class SupplierInvoiceResponse(
    BaseModel
):
    id: int
    invoice_number: str

    supplier_id: int
    supplier_name: str

    purchase_order_id: int | None
    purchase_order_number: str | None

    goods_receipt_id: int | None
    grn_number: str | None

    supplier_invoice_number: str

    invoice_date: datetime
    due_date: date | None

    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal

    paid_amount: Decimal
    balance_amount: Decimal

    is_overdue: bool
    days_overdue: int
    aging_bucket: str

    status: str

    notes: str | None

    is_reversed: bool

    created_at: datetime


class SupplierInvoiceListResponse(
    BaseModel
):
    items: list[
        SupplierInvoiceResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int


class SupplierPaymentCreate(BaseModel):
    supplier_id: int = Field(
        ge=1,
    )

    supplier_invoice_id: int | None = Field(
        default=None,
        ge=1,
    )

    amount: Decimal = Field(
        gt=Decimal("0.00"),
    )

    payment_method: str = Field(
        min_length=1,
        max_length=30,
    )

    reference_number: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class SupplierPaymentReverseRequest(
    BaseModel
):
    reason: str = Field(
        min_length=3,
        max_length=500,
    )


class SupplierPaymentResponse(
    BaseModel
):
    id: int
    payment_number: str

    supplier_id: int
    supplier_name: str

    supplier_invoice_id: int | None
    supplier_invoice_number: str | None

    amount: Decimal

    payment_method: str
    reference_number: str | None

    payment_date: datetime

    status: str
    is_reversed: bool

    notes: str | None

    created_at: datetime


class SupplierPaymentListResponse(
    BaseModel
):
    items: list[
        SupplierPaymentResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int
