from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
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


class CustomerType(str, Enum):
    CASH = "cash"
    CREDIT = "credit"
    INSTALLMENT = "installment"
    DEALER = "dealer"
    WHOLESALE = "wholesale"
    VIP = "vip"


class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class CreditStatus(str, Enum):
    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "customer_number",
            name="uq_customers_company_customer_number",
        ),
        UniqueConstraint(
            "company_id",
            "nic_number",
            name="uq_customers_company_nic_number",
        ),
        UniqueConstraint(
            "company_id",
            "primary_phone",
            name="uq_customers_company_primary_phone",
        ),
        UniqueConstraint(
            "company_id",
            "email",
            name="uq_customers_company_email",
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

    customer_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )

    customer_type: Mapped[str] = mapped_column(
        String(30),
        default=CustomerType.CASH.value,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default=CustomerStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        index=True,
    )

    business_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )

    nic_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    primary_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    secondary_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    sms_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    address_line_1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    address_line_2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    province: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    credit_status: Mapped[str] = mapped_column(
        String(30),
        default=CreditStatus.RESTRICTED.value,
        nullable=False,
    )

    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    sms_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    company: Mapped["Company"] = relationship()
    created_by: Mapped["User"] = relationship(
        foreign_keys=[created_by_id],
    )
    updated_by: Mapped["User | None"] = relationship(
        foreign_keys=[updated_by_id],
    )


from app.models.company import Company
from app.models.user import User
