from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales import PaymentMethod


CashBookEntryType = Literal[
    "cash_in",
    "cash_out",
]


class ManualCashBookEntryCreate(BaseModel):
    entry_type: CashBookEntryType

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

    branch_id: int | None = None

    status: str

    running_balance: Decimal | None = None


class CashBookSummaryResponse(BaseModel):
    opening_balance: Decimal
    cash_in: Decimal
    cash_out: Decimal
    closing_balance: Decimal

    transaction_count: int


class CashBookListResponse(BaseModel):
    items: list[CashBookTransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int

    summary: CashBookSummaryResponse
