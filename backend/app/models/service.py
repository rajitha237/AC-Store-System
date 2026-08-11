from __future__ import annotations

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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


class ServiceJobStatus(str, Enum):
    RECEIVED = "received"
    INSPECTION = "inspection"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REPAIRING = "repairing"
    TESTING = "testing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ServiceJobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ServiceType(str, Enum):
    REPAIR = "repair"
    WARRANTY = "warranty"
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ServiceJobCard(Base):
    __tablename__ = "service_job_cards"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "job_number",
            name="uq_service_job_cards_company_job_number",
        ),
        CheckConstraint(
            "estimated_cost >= 0",
            name="estimated_cost_nonnegative",
        ),
        CheckConstraint(
            "labour_total >= 0",
            name="labour_total_nonnegative",
        ),
        CheckConstraint(
            "parts_total >= 0",
            name="parts_total_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="discount_amount_nonnegative",
        ),
        CheckConstraint(
            "final_amount >= 0",
            name="final_amount_nonnegative",
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

    job_number: Mapped[str | None] = mapped_column(
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

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    sold_serial_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_serial_numbers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    serial_number: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    secondary_serial_number: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    brand_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    model_number: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    item_color: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    service_type: Mapped[str] = mapped_column(
        String(30),
        default=ServiceType.REPAIR.value,
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(30),
        default=ServiceJobPriority.NORMAL.value,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=ServiceJobStatus.RECEIVED.value,
        nullable=False,
        index=True,
    )

    approval_status: Mapped[str] = mapped_column(
        String(30),
        default=ApprovalStatus.NOT_REQUIRED.value,
        nullable=False,
        index=True,
    )

    complaint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reported_issue: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    technician_diagnosis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    work_performed: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    testing_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    accessories_received: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    physical_condition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    special_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    technician_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    receiving_officer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    is_warranty_job: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    warranty_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    warranty_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    related_invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "sales_invoices.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    labour_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    parts_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    final_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    expected_completion_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    approval_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
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

    customer: Mapped["Customer"] = relationship()

    product: Mapped["Product | None"] = relationship(
        foreign_keys=[product_id],
    )

    sold_serial: Mapped[
        "ProductSerialNumber | None"
    ] = relationship(
        foreign_keys=[sold_serial_id],
    )

    related_invoice: Mapped[
        "SalesInvoice | None"
    ] = relationship(
        foreign_keys=[related_invoice_id],
    )

    technician: Mapped["User | None"] = relationship(
        foreign_keys=[technician_id],
    )

    receiving_officer: Mapped["User | None"] = relationship(
        foreign_keys=[receiving_officer_id],
    )

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )

    updated_by: Mapped["User | None"] = relationship(
        foreign_keys=[updated_by_id],
    )

    status_history: Mapped[
        list["ServiceJobStatusHistory"]
    ] = relationship(
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="ServiceJobStatusHistory.created_at",
    )

    parts: Mapped[
        list["ServiceJobPart"]
    ] = relationship(
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="ServiceJobPart.id",
    )

    labour_items: Mapped[
        list["ServiceLabourItem"]
    ] = relationship(
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="ServiceLabourItem.id",
    )

    images: Mapped[
        list["ServiceJobImage"]
    ] = relationship(
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="ServiceJobImage.id",
    )

    checklist_items: Mapped[
        list["ServiceChecklistItem"]
    ] = relationship(
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="ServiceChecklistItem.id",
    )


class ServiceJobStatusHistory(Base):
    __tablename__ = "service_job_status_history"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
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

    job_card: Mapped["ServiceJobCard"] = relationship(
        back_populates="status_history",
    )

    changed_by: Mapped["User"] = relationship(
        foreign_keys=[changed_by_id],
    )


class ServiceJobPart(Base):
    __tablename__ = "service_job_parts"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="unit_cost_nonnegative",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="unit_price_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="line_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
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

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey(
            "warehouses.id",
            ondelete="RESTRICT",
        ),
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

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    stock_movement_id: Mapped[int | None] = mapped_column(
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

    job_card: Mapped["ServiceJobCard"] = relationship(
        back_populates="parts",
    )

    product: Mapped["Product"] = relationship()

    warehouse: Mapped["Warehouse"] = relationship()

    stock_movement: Mapped[
        "StockMovement | None"
    ] = relationship()

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )


class ServiceLabourItem(Base):
    __tablename__ = "service_labour_items"

    __table_args__ = (
        CheckConstraint(
            "hours >= 0",
            name="hours_nonnegative",
        ),
        CheckConstraint(
            "amount >= 0",
            name="amount_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job_card: Mapped["ServiceJobCard"] = relationship(
        back_populates="labour_items",
    )

    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )


class ServiceJobImage(Base):
    __tablename__ = "service_job_images"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    image_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    uploaded_by_id: Mapped[int] = mapped_column(
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

    job_card: Mapped["ServiceJobCard"] = relationship(
        back_populates="images",
    )

    uploaded_by: Mapped["User"] = relationship(
        foreign_keys=[uploaded_by_id],
    )


class ServiceChecklistItem(Base):
    __tablename__ = "service_checklist_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    item_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    completed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job_card: Mapped["ServiceJobCard"] = relationship(
        back_populates="checklist_items",
    )

    completed_by: Mapped["User | None"] = relationship(
        foreign_keys=[completed_by_id],
    )


from app.models.catalog import Product
from app.models.customer import Customer
from app.models.inventory import (
    ProductSerialNumber,
    StockMovement,
    Warehouse,
)
from app.models.sales import SalesInvoice
from app.models.user import User
