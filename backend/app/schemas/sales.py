from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.sales import (
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
)


class SalesItemCreate(BaseModel):
    product_id: int = Field(ge=1)

    warehouse_id: int = Field(ge=1)

    serial_number_id: int | None = Field(
        default=None,
        ge=1,
    )

    quantity: Decimal = Field(
        default=Decimal("1.000"),
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    unit_price: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    description: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("description")
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_line_amounts(
        self,
    ) -> "SalesItemCreate":
        gross = (
            self.quantity
            * self.unit_price
        )

        if (
            self.discount_amount
            > gross
        ):
            raise ValueError(
                "Item discount cannot exceed "
                "line gross amount"
            )

        return self


class SalesInvoiceCreate(BaseModel):
    customer_id: int = Field(ge=1)

    branch_id: int | None = Field(
        default=None,
        ge=1,
    )

    invoice_discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    notes: str | None = None

    items: list[SalesItemCreate] = Field(
        min_length=1,
        max_length=100,
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

    @field_validator("items")
    @classmethod
    def validate_serial_duplicates(
        cls,
        items: list[SalesItemCreate],
    ) -> list[SalesItemCreate]:
        serial_ids = [
            item.serial_number_id
            for item in items
            if item.serial_number_id
            is not None
        ]

        if (
            len(serial_ids)
            != len(set(serial_ids))
        ):
            raise ValueError(
                "The same serial number cannot "
                "appear more than once on an invoice"
            )

        return items


class InitialPaymentCreate(BaseModel):
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
        if value is None:
            return None

        value = value.strip()
        return value or None


class SalesInvoiceConfirmRequest(BaseModel):
    initial_payment: (
        InitialPaymentCreate | None
    ) = None


class SalesInvoiceItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    invoice_id: int

    product_id: int | None
    item_type: str

    serial_number_id: int | None

    description: str | None

    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    line_total: Decimal

    created_at: datetime


class CustomerPaymentResponse(BaseModel):
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


class SalesInvoiceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    company_id: int
    branch_id: int

    invoice_number: str

    customer_id: int

    source_type: str
    source_id: int | None

    invoice_date: datetime

    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    grand_total: Decimal

    credited_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal

    payment_status: str
    invoice_status: str

    notes: str | None

    created_by_id: int
    updated_by_id: int | None

    created_at: datetime
    updated_at: datetime

    items: list[
        SalesInvoiceItemResponse
    ]


class SalesInvoiceDetailResponse(
    SalesInvoiceResponse
):
    customer_name: str
    customer_phone: str

    payments: list[
        CustomerPaymentResponse
    ]


class SalesInvoiceListResponse(BaseModel):
    items: list[
        SalesInvoiceResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int


class PaymentCreate(BaseModel):
    invoice_id: int = Field(
        ge=1
    )

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
        if value is None:
            return None

        value = value.strip()
        return value or None


class InvoiceStatusResponse(BaseModel):
    invoice_id: int
    invoice_number: str

    invoice_status: InvoiceStatus
    payment_status: PaymentStatus

    grand_total: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
