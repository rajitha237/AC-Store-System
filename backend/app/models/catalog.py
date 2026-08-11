from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "code",
            name="uq_product_categories_company_code",
        ),
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_product_categories_company_name",
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

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
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
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parent: Mapped[ProductCategory | None] = relationship(
        remote_side="ProductCategory.id",
    )


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "code",
            name="uq_brands_company_code",
        ),
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_brands_company_name",
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

    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"
    __table_args__ = (
        CheckConstraint(
            "decimal_places >= 0 AND decimal_places <= 6",
            name="ck_units_decimal_places_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    decimal_places: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "product_code",
            name="uq_products_company_product_code",
        ),
        UniqueConstraint(
            "company_id",
            "barcode",
            name="uq_products_company_barcode",
        ),
        CheckConstraint(
            "purchase_cost >= 0",
            name="ck_products_purchase_cost_nonnegative",
        ),
        CheckConstraint(
            "selling_price >= 0",
            name="ck_products_selling_price_nonnegative",
        ),
        CheckConstraint(
            "minimum_selling_price >= 0",
            name="ck_products_minimum_price_nonnegative",
        ),
        CheckConstraint(
            "minimum_selling_price <= selling_price",
            name="ck_products_minimum_not_above_selling",
        ),
        CheckConstraint(
            "warranty_months >= 0",
            name="ck_products_warranty_months_nonnegative",
        ),
        CheckConstraint(
            "reorder_level >= 0",
            name="ck_products_reorder_level_nonnegative",
        ),
        CheckConstraint(
            "reorder_quantity >= 0",
            name="ck_products_reorder_quantity_nonnegative",
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

    product_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "brands.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    unit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "units_of_measure.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    model_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    btu_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    product_type: Mapped[str] = mapped_column(
        String(50),
        default="equipment",
        nullable=False,
        index=True,
    )

    track_serial_numbers: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    purchase_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    minimum_selling_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    warranty_months: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    technical_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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

    category: Mapped[ProductCategory] = relationship()
    brand: Mapped[Brand | None] = relationship()
    unit: Mapped[UnitOfMeasure] = relationship()
