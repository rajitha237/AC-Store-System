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
    Integer,
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


class InstallmentPlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InstallmentScheduleStatus(
    str,
    Enum,
):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"


class InstallmentFrequency(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "agreement_number",
            name=(
                "uq_installment_plans_"
                "company_agreement"
            ),
        ),
        UniqueConstraint(
            "invoice_id",
            name=(
                "uq_installment_plans_"
                "invoice"
            ),
        ),
        CheckConstraint(
            "installment_count > 0",
            name=(
                "ck_installment_plans_"
                "count_positive"
            ),
        ),
        CheckConstraint(
            "financed_amount > 0",
            name=(
                "ck_installment_plans_"
                "financed_positive"
            ),
        ),
        CheckConstraint(
            "total_paid >= 0",
            name=(
                "ck_installment_plans_"
                "paid_nonnegative"
            ),
        ),
        CheckConstraint(
            "outstanding_amount >= 0",
            name=(
                "ck_installment_plans_"
                "outstanding_nonnegative"
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

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
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

    agreement_number: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    first_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    frequency: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    installment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    principal_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    interest_rate: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )

    interest_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    financed_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    scheduled_installment_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    total_paid: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    outstanding_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    grace_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=(
            InstallmentPlanStatus
            .ACTIVE
            .value
        ),
        server_default=(
            InstallmentPlanStatus
            .ACTIVE
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

    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    schedules: Mapped[
        list["InstallmentSchedule"]
    ] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by=(
            "InstallmentSchedule."
            "installment_number"
        ),
        lazy="selectin",
    )

    allocations: Mapped[
        list[
            "InstallmentPaymentAllocation"
        ]
    ] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InstallmentSchedule(Base):
    __tablename__ = "installment_schedules"

    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "installment_number",
            name=(
                "uq_installment_schedule_"
                "plan_number"
            ),
        ),
        CheckConstraint(
            "amount_due > 0",
            name=(
                "ck_installment_schedule_"
                "due_positive"
            ),
        ),
        CheckConstraint(
            "amount_paid >= 0",
            name=(
                "ck_installment_schedule_"
                "paid_nonnegative"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey(
            "installment_plans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    installment_number: Mapped[
        int
    ] = mapped_column(
        Integer,
        nullable=False,
    )

    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    amount_due: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    amount_paid: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=(
            InstallmentScheduleStatus
            .PENDING
            .value
        ),
        server_default=(
            InstallmentScheduleStatus
            .PENDING
            .value
        ),
        index=True,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    plan: Mapped[
        "InstallmentPlan"
    ] = relationship(
        back_populates="schedules",
    )

    allocations: Mapped[
        list[
            "InstallmentPaymentAllocation"
        ]
    ] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


class InstallmentPaymentAllocation(Base):
    __tablename__ = (
        "installment_payment_allocations"
    )

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name=(
                "ck_installment_allocation_"
                "amount_positive"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey(
            "installment_plans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    schedule_id: Mapped[int] = mapped_column(
        ForeignKey(
            "installment_schedules.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    payment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customer_payments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    principal_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    interest_amount: Mapped[
        Decimal
    ] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    is_reversed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    plan: Mapped[
        "InstallmentPlan"
    ] = relationship(
        back_populates="allocations",
    )

    schedule: Mapped[
        "InstallmentSchedule"
    ] = relationship(
        back_populates="allocations",
    )
