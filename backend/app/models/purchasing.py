from __future__ import annotations

from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "purchase_order_number",
            name=(
                "uq_purchase_orders_"
                "company_number"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey(
            "warehouses.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    purchase_order_number: Mapped[
        str | None
    ] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=PurchaseOrderStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    order_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        index=True,
    )

    expected_date: Mapped[
        date | None
    ] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    discount_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    tax_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    grand_total: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    approved_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    approved_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    cancelled_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancellation_reason: Mapped[
        str | None
    ] = mapped_column(
        String(250),
        nullable=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    updated_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[
        list["PurchaseOrderItem"]
    ] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    __table_args__ = (
        UniqueConstraint(
            "purchase_order_id",
            "product_id",
            name=(
                "uq_purchase_order_items_"
                "order_product"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    purchase_order_id: Mapped[
        int
    ] = mapped_column(
        ForeignKey(
            "purchase_orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    received_quantity: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    discount_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    tax_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    line_total: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    purchase_order: Mapped[
        "PurchaseOrder"
    ] = relationship(
        back_populates="items",
    )


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "grn_number",
            name=(
                "uq_goods_receipts_"
                "company_grn_number"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "purchase_orders.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey(
            "warehouses.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    grn_number: Mapped[
        str | None
    ] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    delivery_note_number: Mapped[
        str | None
    ] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    received_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    items: Mapped[
        list["GoodsReceiptItem"]
    ] = relationship(
        back_populates="goods_receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    goods_receipt_id: Mapped[int] = mapped_column(
        ForeignKey(
            "goods_receipts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    purchase_order_item_id: Mapped[int] = mapped_column(
        ForeignKey(
            "purchase_order_items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity_received: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_cost: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    goods_receipt: Mapped[
        "GoodsReceipt"
    ] = relationship(
        back_populates="items",
    )

    serials: Mapped[
        list["GoodsReceiptSerial"]
    ] = relationship(
        back_populates="goods_receipt_item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class GoodsReceiptSerial(Base):
    __tablename__ = "goods_receipt_serials"

    __table_args__ = (
        UniqueConstraint(
            "product_serial_number_id",
            name=(
                "uq_goods_receipt_serials_"
                "product_serial"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    goods_receipt_item_id: Mapped[
        int
    ] = mapped_column(
        ForeignKey(
            "goods_receipt_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_serial_number_id: Mapped[
        int
    ] = mapped_column(
        ForeignKey(
            "product_serial_numbers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    serial_number: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    secondary_serial_number: Mapped[
        str | None
    ] = mapped_column(
        String(150),
        nullable=True,
    )

    goods_receipt_item: Mapped[
        "GoodsReceiptItem"
    ] = relationship(
        back_populates="serials",
    )


class SupplierInvoiceStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    PAID = "paid"
    REVERSED = "reversed"


class SupplierPaymentStatus(str, Enum):
    POSTED = "posted"
    REVERSED = "reversed"


class SupplierInvoice(Base):
    __tablename__ = "supplier_invoices"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "invoice_number",
            name=(
                "uq_supplier_invoices_"
                "company_invoice_number"
            ),
        ),
        UniqueConstraint(
            "company_id",
            "supplier_id",
            "supplier_invoice_number",
            name=(
                "uq_supplier_invoices_"
                "supplier_reference"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    purchase_order_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "purchase_orders.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    goods_receipt_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "goods_receipts.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    invoice_number: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    supplier_invoice_number: Mapped[
        str
    ] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    invoice_date: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    due_date: Mapped[
        date | None
    ] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    subtotal: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    discount_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    tax_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    grand_total: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    paid_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    balance_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=(
            SupplierInvoiceStatus
            .DRAFT
            .value
        ),
        index=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    posted_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    posted_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_reversed: Mapped[
        bool
    ] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    reversed_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    reversed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reversal_reason: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payments: Mapped[
        list["SupplierPayment"]
    ] = relationship(
        back_populates="supplier_invoice",
        lazy="selectin",
    )


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "payment_number",
            name=(
                "uq_supplier_payments_"
                "company_payment_number"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    supplier_invoice_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "supplier_invoices.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    payment_number: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    payment_date: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    payment_method: Mapped[
        str
    ] = mapped_column(
        String(30),
        nullable=False,
    )

    reference_number: Mapped[
        str | None
    ] = mapped_column(
        String(150),
        nullable=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=(
            SupplierPaymentStatus
            .POSTED
            .value
        ),
    )

    is_reversed: Mapped[
        bool
    ] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    reversed_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    reversed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reversal_reason: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    supplier_invoice: Mapped[
        "SupplierInvoice | None"
    ] = relationship(
        back_populates="payments",
    )
