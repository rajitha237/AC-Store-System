from __future__ import annotations

from datetime import date, datetime, time, UTC
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class LegacyServiceJob(Base):
    """
    Read-only historical service-job header imported from the legacy system.

    IMPORTANT:
    - Must never mutate current stock.
    - Must never create stock movements.
    - Must never create product serial records.
    - Must never create live sales invoices/payments/receipts.
    - legacy_job_id is the authoritative migration lineage.
    - invoice_code is intentionally NOT unique.
    """

    __tablename__ = "legacy_service_jobs"

    __table_args__ = (
        UniqueConstraint(
            "legacy_job_id",
            name="uq_legacy_service_jobs_legacy_job_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    legacy_job_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    invoice_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    job_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    job_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    reference_no: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    sale_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    legacy_customer_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    customer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    customer_phone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    customer_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    bill_discount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    bill_discount_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    source_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    profit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    pay_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    rest_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    cash_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    cheque_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    card_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    bank_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    over_balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    balance_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    legacy_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    legacy_user_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Historical source value only.
    # Must NOT be interpreted automatically as completion date.
    legacy_service_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    legacy_warranty_period: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    migration_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Operational management metadata only.
    # These fields do NOT replace or rewrite the legacy source history.
    management_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="received",
        server_default="received",
        index=True,
    )

    status_remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status_updated_by_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    lines: Mapped[list["LegacyServiceJobLine"]] = relationship(
        back_populates="service_job",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="selectin",
    )


class LegacyServiceJobLine(Base):
    """
    Read-only historical service-job detail line.

    line_type is expected to preserve the legacy source value:
    - service
    - item

    An item line is historical only and MUST NOT update current inventory.
    """

    __tablename__ = "legacy_service_job_lines"

    __table_args__ = (
        UniqueConstraint(
            "legacy_service_job_id",
            "line_number",
            name="uq_legacy_service_job_lines_job_line",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    legacy_service_job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "legacy_service_jobs.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    legacy_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    line_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3),
        nullable=False,
        default=Decimal("0.000"),
    )

    rate: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    discount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    unit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Historical raw serial value only.
    # No uniqueness constraint and no operational ProductSerial creation.
    serial_no: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    service_job: Mapped[LegacyServiceJob] = relationship(
        back_populates="lines",
    )
