from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



def utc_now() -> datetime:
    return datetime.now(UTC)


class LegacyGoodsReceipt(Base):
    """
    Read-only historical GRN imported from the legacy system.

    IMPORTANT:
    These rows are historical records only.
    They must never mutate inventory, stock movements,
    serial numbers, supplier payables, purchase orders,
    supplier invoices, or supplier payments.
    """

    __tablename__ = "legacy_goods_receipts"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "source_system",
            "legacy_internal_id",
            name="uq_legacy_grn_company_source_internal",
        ),
        UniqueConstraint(
            "company_id",
            "source_system",
            "legacy_grn_number",
            name="uq_legacy_grn_company_source_number",
        ),
        Index(
            "ix_legacy_grn_company_receipt_date",
            "company_id",
            "receipt_date",
        ),
        Index(
            "ix_legacy_grn_company_supplier",
            "company_id",
            "supplier_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
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

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    legacy_grn_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    legacy_internal_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    legacy_supplier_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    legacy_grn_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reference_invoice_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    receipt_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    net_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    outstanding_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    legacy_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="legacy_ac_store",
    )

    source_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    items: Mapped[list["LegacyGoodsReceiptItem"]] = relationship(
        back_populates="legacy_goods_receipt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LegacyGoodsReceiptItem.id",
    )


class LegacyGoodsReceiptItem(Base):
    """
    Historical legacy GRN item.

    product_id is optional because unresolved legacy products
    are allowed. Legacy code/name are always preserved.
    """

    __tablename__ = "legacy_goods_receipt_items"

    __table_args__ = (
        UniqueConstraint(
            "legacy_goods_receipt_id",
            "legacy_item_id",
            name="uq_legacy_grn_item_receipt_item",
        ),
        Index(
            "ix_legacy_grn_item_product",
            "product_id",
        ),
        Index(
            "ix_legacy_grn_item_code",
            "legacy_product_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    legacy_goods_receipt_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legacy_goods_receipts.id",
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
    )

    legacy_item_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    legacy_created_grn_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    legacy_product_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    legacy_product_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    retail_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    wholesale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    temporary_stock: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 3),
        nullable=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    expiry_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    legacy_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    serial_numbers_json: Mapped[Any | None] = mapped_column(
        JSON,
        nullable=True,
    )

    imeis_json: Mapped[Any | None] = mapped_column(
        JSON,
        nullable=True,
    )

    source_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    legacy_goods_receipt: Mapped["LegacyGoodsReceipt"] = relationship(
        back_populates="items",
    )
