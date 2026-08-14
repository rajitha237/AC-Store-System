from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.models.sales import PaymentMethod


class InstallmentPlanCreate(BaseModel):
    invoice_id: int = Field(
        ge=1,
    )

    first_due_date: date

    frequency: str = Field(
        default="monthly",
        pattern=(
            "^(weekly|biweekly|monthly)$"
        ),
    )

    installment_count: int = Field(
        ge=1,
        le=120,
    )

    grace_days: int = Field(
        default=0,
        ge=0,
        le=90,
    )

    interest_rate: Decimal = Field(
        default=Decimal("0.0000"),
        ge=Decimal("0.0000"),
        le=Decimal("100.0000"),
        max_digits=8,
        decimal_places=4,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class InstallmentPaymentCreate(
    BaseModel
):
    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    payment_method: PaymentMethod = (
        PaymentMethod.CASH
    )

    reference_number: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )


class InstallmentPaymentReverse(
    BaseModel
):
    reason: str = Field(
        min_length=3,
        max_length=500,
    )


class InstallmentPlanCancel(
    BaseModel
):
    reason: str = Field(
        min_length=3,
        max_length=500,
    )


class InstallmentScheduleResponse(
    BaseModel
):
    id: int
    installment_number: int
    due_date: date

    amount_due: Decimal
    amount_paid: Decimal
    remaining_amount: Decimal

    status: str
    is_overdue: bool
    days_overdue: int


class InstallmentPlanSummaryResponse(
    BaseModel
):
    id: int

    agreement_number: str

    customer_id: int
    customer_name: str

    invoice_id: int
    invoice_number: str

    start_date: date
    first_due_date: date

    frequency: str
    installment_count: int

    principal_amount: Decimal
    interest_rate: Decimal
    interest_amount: Decimal
    financed_amount: Decimal

    scheduled_installment_amount: (
        Decimal
    )

    total_paid: Decimal
    outstanding_amount: Decimal

    grace_days: int
    status: str

    overdue_installment_count: int
    overdue_amount: Decimal

    next_due_date: date | None
    next_due_amount: Decimal | None

    created_at: datetime


class InstallmentPlanDetailResponse(
    InstallmentPlanSummaryResponse
):
    notes: str | None

    schedules: list[
        InstallmentScheduleResponse
    ]


class InstallmentPlanListResponse(
    BaseModel
):
    items: list[
        InstallmentPlanSummaryResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int


class InstallmentPaymentResponse(
    BaseModel
):
    message: str

    payment_id: int
    receipt_number: str

    plan_id: int
    agreement_number: str

    invoice_id: int
    invoice_number: str

    customer_id: int

    amount: Decimal
    principal_amount: Decimal
    interest_amount: Decimal

    payment_method: str

    plan_total_paid: Decimal
    plan_outstanding_amount: Decimal

    invoice_paid_amount: Decimal
    invoice_balance_amount: Decimal

    customer_balance: Decimal

    allocations: list[
        dict
    ]


class CustomerLedgerEntryResponse(
    BaseModel
):
    transaction_date: datetime

    transaction_type: str

    reference: str

    description: str

    debit: Decimal
    credit: Decimal

    running_balance: Decimal

    invoice_id: int | None = None
    payment_id: int | None = None


class CustomerLedgerResponse(
    BaseModel
):
    customer_id: int
    customer_number: str | None
    customer_name: str

    opening_balance: Decimal

    total_debits: Decimal
    total_credits: Decimal

    closing_balance: Decimal

    date_from: date | None
    date_to: date | None

    entries: list[
        CustomerLedgerEntryResponse
    ]


class CustomerStatementResponse(
    CustomerLedgerResponse
):
    generated_at: datetime
