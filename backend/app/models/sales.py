from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    ONLINE = "online"
    OTHER = "other"


class InvoiceSourceType(str, Enum):
    SALES = "sales"
    SERVICE_JOB = "service_job"


class InvoiceItemType(str, Enum):
    PRODUCT = "product"
    SERVICE_PART = "service_part"
    LABOUR = "labour"


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "invoice_number",
            name="uq_sales_invoices_company_invoice_number",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_sales_invoices_subtotal_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_sales_invoices_discount_nonnegative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="ck_sales_invoices_tax_nonnegative",
        ),
        CheckConstraint(
            "grand_total >= 0",
            name="ck_sales_invoices_grand_total_nonnegative",
        ),
        CheckConstraint(
            "paid_amount >= 0",
            name="ck_sales_invoices_paid_nonnegative",
        ),
        CheckConstraint(
            "balance_amount >= 0",
            name="ck_sales_invoices_balance_nonnegative",
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

    invoice_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(30),
        default=InvoiceSourceType.SALES.value,
        server_default=InvoiceSourceType.SALES.value,
        nullable=False,
        index=True,
    )

    source_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    credited_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )

    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    payment_status: Mapped[str] = mapped_column(
        String(30),
        default=PaymentStatus.UNPAID.value,
        nullable=False,
        index=True,
    )

    invoice_status: Mapped[str] = mapped_column(
        String(30),
        default=InvoiceStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
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

    updated_by_id: Mapped[int | None] = mapped_column(
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

    customer: Mapped["Customer"] = relationship()

    items: Mapped[list["SalesInvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="SalesInvoiceItem.id",
    )

    payments: Mapped[list["CustomerPayment"]] = relationship(
        back_populates="invoice",
        order_by="CustomerPayment.payment_date",
    )

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )

    updated_by: Mapped["User | None"] = relationship(
        foreign_keys=[updated_by_id],
    )


class SalesInvoiceItem(Base):
    __tablename__ = "sales_invoice_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_sales_invoice_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_sales_invoice_items_unit_price_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_sales_invoice_items_discount_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="ck_sales_invoice_items_line_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_invoices.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    item_type: Mapped[str] = mapped_column(
        String(30),
        default=InvoiceItemType.PRODUCT.value,
        server_default=InvoiceItemType.PRODUCT.value,
        nullable=False,
        index=True,
    )

    serial_number_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_serial_numbers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    invoice: Mapped["SalesInvoice"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product | None"] = relationship()

    serial_number: Mapped[
        "ProductSerialNumber | None"
    ] = relationship()


class CustomerPayment(Base):
    __tablename__ = "customer_payments"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "receipt_number",
            name="uq_customer_payments_company_receipt_number",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_customer_payments_amount_positive",
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

    receipt_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "sales_invoices.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        default=PaymentMethod.CASH.value,
        nullable=False,
        index=True,
    )

    reference_number: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_reversed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )

    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reversal_reason: Mapped[str | None] = mapped_column(
        Text,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    invoice: Mapped["SalesInvoice | None"] = relationship(
        back_populates="payments",
    )

    customer: Mapped["Customer"] = relationship()

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )


from app.models.catalog import Product
from app.models.customer import Customer
from app.models.inventory import ProductSerialNumber
from app.models.user import User
