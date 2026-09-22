from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.sales import PaymentMethod


CashBookEntryType = Literal[
    "cash_in",
    "cash_out",
]


class ManualCashBookEntryCreate(BaseModel):
    entry_type: CashBookEntryType
    entry_date: date | None = None

    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
    )

    payment_method: PaymentMethod = (
        PaymentMethod.CASH
    )

    category: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str = Field(
        min_length=1,
        max_length=255,
    )

    reference_number: str | None = Field(
        default=None,
        max_length=100,
    )

    cheque_date: date | None = None

    notes: str | None = None

    @model_validator(mode="after")
    def validate_cheque_date(self):
        if (
            self.payment_method == PaymentMethod.CHEQUE
            and self.cheque_date is None
        ):
            raise ValueError(
                "Cheque date is required for cheque entries"
            )

        return self


class ManualCashBookEntryUpdate(BaseModel):
    entry_type: CashBookEntryType
    entry_date: date

    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
    )

    payment_method: PaymentMethod = (
        PaymentMethod.CASH
    )

    category: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str = Field(
        min_length=1,
        max_length=255,
    )

    reference_number: str | None = Field(
        default=None,
        max_length=100,
    )

    cheque_date: date | None = None

    notes: str | None = None

    @model_validator(mode="after")
    def validate_cheque_date(self):
        if (
            self.payment_method == PaymentMethod.CHEQUE
            and self.cheque_date is None
        ):
            raise ValueError(
                "Cheque date is required for cheque entries"
            )

        return self


class ManualChequeClearRequest(BaseModel):
    notes: str | None = None


class ManualCashBookEntryReverseRequest(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=255,
    )

    notes: str | None = None


class ManualCashBookEntryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    company_id: int
    branch_id: int

    entry_number: str
    entry_type: str
    entry_date: datetime

    amount: Decimal
    payment_method: str

    category: str
    description: str

    reference_number: str | None

    cheque_date: date | None
    cheque_status: str | None
    cheque_cleared_at: datetime | None
    cheque_cleared_by_id: int | None

    notes: str | None

    created_by_id: int

    reversed_at: datetime | None
    reversed_by_id: int | None
    reversal_reason: str | None

    created_at: datetime
    updated_at: datetime


class CashBookTransactionResponse(BaseModel):
    source_type: str
    source_id: int
    source_reference: str | None = None

    direction: CashBookEntryType

    transaction_date: datetime
    amount: Decimal
    payment_method: str

    category: str
    description: str

    reference_number: str | None = None
    notes: str | None = None

    branch_id: int | None = None

    status: str

    cheque_date: date | None = None
    cheque_status: str | None = None
    cheque_cleared_at: datetime | None = None

    can_edit: bool = False
    can_delete: bool = False
    can_confirm_cheque: bool = False

    running_balance: Decimal | None = None


class CashBookSummaryResponse(BaseModel):
    opening_balance: Decimal
    cash_in: Decimal
    cash_out: Decimal
    closing_balance: Decimal

    cash_method_in: Decimal = Decimal("0.00")
    cash_method_out: Decimal = Decimal("0.00")

    bank_transfer_in: Decimal = Decimal("0.00")
    bank_transfer_out: Decimal = Decimal("0.00")

    card_in: Decimal = Decimal("0.00")
    card_out: Decimal = Decimal("0.00")

    cheque_in: Decimal = Decimal("0.00")
    cheque_out: Decimal = Decimal("0.00")
    cheque_pending_out: Decimal = Decimal("0.00")

    transaction_count: int


class CashBookListResponse(BaseModel):
    items: list[CashBookTransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int

    summary: CashBookSummaryResponse
