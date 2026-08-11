from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


class WarehouseType(str, Enum):
    MAIN = "main"
    SERVICE = "service"
    FAULTY = "faulty"
    RETURNED = "returned"
    SUPPLIER_CLAIM = "supplier_claim"


class SerialNumberStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    UNDER_SERVICE = "under_service"
    CUSTOMER_RETURNED = "customer_returned"
    FAULTY = "faulty"
    SUPPLIER_CLAIM = "supplier_claim"
    REPLACEMENT_ISSUED = "replacement_issued"
    DAMAGED = "damaged"
    WRITTEN_OFF = "written_off"


class StockMovementType(str, Enum):
    OPENING_BALANCE = "opening_balance"
    PURCHASE_RECEIPT = "purchase_receipt"
    SALE_ISSUE = "sale_issue"
    SALE_RETURN = "sale_return"
    SALE_RETURN_REVERSAL = "sale_return_reversal"
    REPLACEMENT_ISSUE = "replacement_issue"
    SUPPLIER_RETURN = "supplier_return"
    SERVICE_USAGE = "service_usage"
    ADJUSTMENT_INCREASE = "adjustment_increase"
    ADJUSTMENT_DECREASE = "adjustment_decrease"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    WRITE_OFF = "write_off"


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "code",
            name="uq_warehouses_branch_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    warehouse_type: Mapped[str] = mapped_column(
        String(30),
        default=WarehouseType.MAIN.value,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id",
            "product_id",
            name="uq_stock_items_warehouse_product",
        ),
        CheckConstraint(
            "quantity_on_hand >= 0",
            name="ck_stock_items_quantity_nonnegative",
        ),
        CheckConstraint(
            "quantity_reserved >= 0",
            name="ck_stock_items_reserved_nonnegative",
        ),
        CheckConstraint(
            "quantity_reserved <= quantity_on_hand",
            name="ck_stock_items_reserved_not_above_on_hand",
        ),
        CheckConstraint(
            "average_cost >= 0",
            name="ck_stock_items_average_cost_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_on_hand: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    quantity_reserved: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    warehouse: Mapped["Warehouse"] = relationship()
    product: Mapped["Product"] = relationship()


class ProductSerialNumber(Base):
    __tablename__ = "product_serial_numbers"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "serial_number",
            name="uq_product_serial_numbers_company_serial",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    serial_number: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    secondary_serial_number: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default=SerialNumberStatus.AVAILABLE.value,
        nullable=False,
        index=True,
    )

    current_customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    warranty_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    warranty_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sold_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
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

    product: Mapped["Product"] = relationship()
    warehouse: Mapped["Warehouse | None"] = relationship()
    supplier: Mapped["Supplier | None"] = relationship()
    current_customer: Mapped["Customer | None"] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            "quantity != 0",
            name="ck_stock_movements_quantity_nonzero",
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="ck_stock_movements_unit_cost_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
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

    movement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    reference_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    movement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    warehouse: Mapped["Warehouse"] = relationship()
    product: Mapped["Product"] = relationship()
    serial_number: Mapped[
        "ProductSerialNumber | None"
    ] = relationship()


from app.models.catalog import Product
from app.models.customer import Customer
from app.models.supplier import Supplier
