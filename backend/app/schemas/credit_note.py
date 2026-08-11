from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.sales import PaymentMethod


def clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


class CreditNoteCreate(BaseModel):
    return_id: int = Field(
        ge=1
    )

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class CreditNoteApprovalRequest(BaseModel):
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class RefundCreate(BaseModel):
    credit_note_id: int = Field(
        ge=1
    )

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    refund_method: PaymentMethod = (
        PaymentMethod.CASH
    )

    reference_number: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator(
        "reference_number",
        "notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class FinancialReversalRequest(BaseModel):
    reason: str = Field(
        min_length=3,
        max_length=5000,
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Reversal reason must contain "
                "at least 3 characters"
            )

        return value


class CustomerRefundResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    company_id: int
    branch_id: int

    refund_number: str

    credit_note_id: int
    return_id: int
    invoice_id: int
    customer_id: int

    amount: Decimal

    refund_method: str
    status: str

    reference_number: str | None
    notes: str | None

    posted_by_id: int | None
    posted_at: datetime | None

    is_reversed: bool
    reversed_by_id: int | None
    reversed_at: datetime | None
    reversal_reason: str | None

    created_by_id: int
    created_at: datetime


class CreditNoteResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    company_id: int
    branch_id: int

    credit_note_number: str

    invoice_id: int
    return_id: int
    customer_id: int

    amount: Decimal
    status: str

    reason: str
    notes: str | None

    approved_by_id: int | None
    approved_at: datetime | None

    posted_by_id: int | None
    posted_at: datetime | None

    is_reversed: bool
    reversed_by_id: int | None
    reversed_at: datetime | None
    reversal_reason: str | None

    created_by_id: int
    created_at: datetime
    updated_at: datetime


class CreditNoteDetailResponse(
    CreditNoteResponse
):
    invoice_number: str
    return_number: str

    customer_name: str
    customer_phone: str

    invoice_grand_total: Decimal
    invoice_paid_amount: Decimal
    invoice_balance_amount: Decimal

    active_refund_total: Decimal
    refundable_overpayment: Decimal

    refunds: list[
        CustomerRefundResponse
    ]
