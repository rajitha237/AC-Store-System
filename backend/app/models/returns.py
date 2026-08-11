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


class ReturnType(str, Enum):
    SALES_RETURN = "sales_return"
    WARRANTY_RETURN = "warranty_return"


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    INSPECTION = "inspection"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReturnResolution(str, Enum):
    PENDING = "pending"
    REFUND = "refund"
    REPLACEMENT = "replacement"
    WARRANTY_SERVICE = "warranty_service"
    STORE_CREDIT = "store_credit"
    REJECTED = "rejected"


class ReturnItemCondition(str, Enum):
    UNOPENED = "unopened"
    GOOD = "good"
    OPENED = "opened"
    FAULTY = "faulty"
    DAMAGED = "damaged"


class SalesReturn(Base):
    __tablename__ = "sales_returns"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "return_number",
            name="uq_sales_returns_company_return_number",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_sales_returns_subtotal_nonnegative",
        ),
        CheckConstraint(
            "refund_amount >= 0",
            name="ck_sales_returns_refund_nonnegative",
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

    return_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_invoices.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
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

    return_type: Mapped[str] = mapped_column(
        String(30),
        default=ReturnType.SALES_RETURN.value,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=ReturnStatus.REQUESTED.value,
        nullable=False,
        index=True,
    )

    resolution: Mapped[str] = mapped_column(
        String(30),
        default=ReturnResolution.PENDING.value,
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    inspection_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    approval_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    refund_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
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

    invoice: Mapped["SalesInvoice"] = relationship()

    customer: Mapped["Customer"] = relationship()

    items: Mapped[list["SalesReturnItem"]] = relationship(
        back_populates="sales_return",
        cascade="all, delete-orphan",
        order_by="SalesReturnItem.id",
    )

    status_history: Mapped[
        list["SalesReturnStatusHistory"]
    ] = relationship(
        back_populates="sales_return",
        cascade="all, delete-orphan",
        order_by="SalesReturnStatusHistory.created_at",
    )

    approved_by: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by_id],
    )

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )

    updated_by: Mapped["User | None"] = relationship(
        foreign_keys=[updated_by_id],
    )


class SalesReturnItem(Base):
    __tablename__ = "sales_return_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_sales_return_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_sales_return_items_unit_price_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="ck_sales_return_items_line_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    return_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_returns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    invoice_item_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_invoice_items.id",
            ondelete="RESTRICT",
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

    serial_number_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_serial_numbers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    condition: Mapped[str] = mapped_column(
        String(30),
        default=ReturnItemCondition.GOOD.value,
        nullable=False,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    destination_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "warehouses.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    stock_movement_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "stock_movements.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    replacement_product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    replacement_serial_number_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_serial_numbers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    replacement_stock_movement_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "stock_movements.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sales_return: Mapped["SalesReturn"] = relationship(
        back_populates="items",
    )

    invoice_item: Mapped["SalesInvoiceItem"] = relationship()

    product: Mapped["Product | None"] = relationship(
        foreign_keys=[product_id],
    )

    serial_number: Mapped[
        "ProductSerialNumber | None"
    ] = relationship(
        foreign_keys=[serial_number_id],
    )

    destination_warehouse: Mapped[
        "Warehouse | None"
    ] = relationship(
        foreign_keys=[destination_warehouse_id],
    )

    stock_movement: Mapped[
        "StockMovement | None"
    ] = relationship(
        foreign_keys=[stock_movement_id],
    )

    replacement_product: Mapped[
        "Product | None"
    ] = relationship(
        foreign_keys=[replacement_product_id],
    )

    replacement_serial_number: Mapped[
        "ProductSerialNumber | None"
    ] = relationship(
        foreign_keys=[replacement_serial_number_id],
    )

    replacement_stock_movement: Mapped[
        "StockMovement | None"
    ] = relationship(
        foreign_keys=[replacement_stock_movement_id],
    )


class SalesReturnStatusHistory(Base):
    __tablename__ = "sales_return_status_history"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    return_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_returns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    old_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    changed_by_id: Mapped[int] = mapped_column(
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
        index=True,
    )

    sales_return: Mapped["SalesReturn"] = relationship(
        back_populates="status_history",
    )

    changed_by: Mapped["User"] = relationship()
