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


class PaymentReceiveRequest(BaseModel):
    invoice_id: int = Field(ge=1)

    amount: Decimal = Field(
        gt=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    payment_method: PaymentMethod = PaymentMethod.CASH

    reference_number: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = None

    @field_validator(
        "reference_number",
        "notes",
    )
    @classmethod
    def normalize_text(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class PaymentReverseRequest(BaseModel):
    reason: str = Field(
        min_length=3,
        max_length=500,
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
                "Reversal reason is required"
            )

        return value


class PaymentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    company_id: int
    branch_id: int
    receipt_number: str
    customer_id: int
    invoice_id: int | None

    payment_date: datetime
    amount: Decimal
    payment_method: str

    reference_number: str | None
    notes: str | None

    is_reversed: bool
    reversed_at: datetime | None
    reversal_reason: str | None

    created_by_id: int
    created_at: datetime


class PaymentDetailResponse(
    PaymentResponse
):
    invoice_number: str | None
    customer_number: str
    customer_name: str
    customer_phone: str

    invoice_grand_total: Decimal | None
    invoice_paid_amount: Decimal | None
    invoice_balance_amount: Decimal | None
    invoice_payment_status: str | None


class PaymentListResponse(BaseModel):
    items: list[PaymentDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentTransactionResponse(BaseModel):
    message: str

    payment: PaymentDetailResponse

    invoice_id: int
    invoice_number: str

    grand_total: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    payment_status: str

    customer_id: int
    customer_balance: Decimal
