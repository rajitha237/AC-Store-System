from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class CreditNoteStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"


class RefundStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    REVERSED = "reversed"


class CreditNote(Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "credit_note_number",
            name=(
                "uq_credit_notes_company_"
                "credit_note_number"
            ),
        ),
        UniqueConstraint(
            "return_id",
            name="uq_credit_notes_return_id",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_credit_notes_amount_positive",
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

    credit_note_number: Mapped[
        str | None
    ] = mapped_column(
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

    return_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_returns.id",
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

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=CreditNoteStatus.DRAFT.value,
        server_default=(
            CreditNoteStatus.DRAFT.value
        ),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
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

    posted_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    posted_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_reversed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
        index=True,
    )

    reversed_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
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

    invoice: Mapped[
        "SalesInvoice"
    ] = relationship()

    sales_return: Mapped[
        "SalesReturn"
    ] = relationship()

    customer: Mapped[
        "Customer"
    ] = relationship()

    approved_by: Mapped[
        "User | None"
    ] = relationship(
        foreign_keys=[approved_by_id],
    )

    posted_by: Mapped[
        "User | None"
    ] = relationship(
        foreign_keys=[posted_by_id],
    )

    reversed_by: Mapped[
        "User | None"
    ] = relationship(
        foreign_keys=[reversed_by_id],
    )

    created_by: Mapped[
        "User"
    ] = relationship(
        foreign_keys=[created_by_id],
    )

    refunds: Mapped[
        list["CustomerRefund"]
    ] = relationship(
        back_populates="credit_note",
        order_by="CustomerRefund.id",
    )


class CustomerRefund(Base):
    __tablename__ = "customer_refunds"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "refund_number",
            name=(
                "uq_customer_refunds_company_"
                "refund_number"
            ),
        ),
        CheckConstraint(
            "amount > 0",
            name=(
                "ck_customer_refunds_"
                "amount_positive"
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

    refund_number: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    credit_note_id: Mapped[int] = mapped_column(
        ForeignKey(
            "credit_notes.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    return_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sales_returns.id",
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

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    refund_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=RefundStatus.PENDING.value,
        server_default=(
            RefundStatus.PENDING.value
        ),
        nullable=False,
        index=True,
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

    posted_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    posted_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_reversed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
        index=True,
    )

    reversed_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
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
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    credit_note: Mapped[
        "CreditNote"
    ] = relationship(
        back_populates="refunds",
    )

    sales_return: Mapped[
        "SalesReturn"
    ] = relationship()

    invoice: Mapped[
        "SalesInvoice"
    ] = relationship()

    customer: Mapped[
        "Customer"
    ] = relationship()

    posted_by: Mapped[
        "User | None"
    ] = relationship(
        foreign_keys=[posted_by_id],
    )

    reversed_by: Mapped[
        "User | None"
    ] = relationship(
        foreign_keys=[reversed_by_id],
    )

    created_by: Mapped[
        "User"
    ] = relationship(
        foreign_keys=[created_by_id],
    )
