from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.returns import (
    ReturnItemCondition,
    ReturnResolution,
    ReturnStatus,
    ReturnType,
)


def clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


class SalesReturnItemCreate(BaseModel):
    invoice_item_id: int = Field(
        ge=1
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    condition: ReturnItemCondition = (
        ReturnItemCondition.GOOD
    )

    reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    destination_warehouse_id: int | None = Field(
        default=None,
        ge=1,
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class SalesReturnCreate(BaseModel):
    invoice_id: int = Field(
        ge=1
    )

    return_type: ReturnType = (
        ReturnType.SALES_RETURN
    )

    reason: str = Field(
        min_length=3,
        max_length=5000,
    )

    items: list[SalesReturnItemCreate] = Field(
        min_length=1,
        max_length=100,
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
                "Return reason must contain "
                "at least 3 characters"
            )

        return value

    @model_validator(mode="after")
    def validate_duplicate_items(
        self,
    ) -> "SalesReturnCreate":
        invoice_item_ids = [
            item.invoice_item_id
            for item in self.items
        ]

        if (
            len(invoice_item_ids)
            != len(set(invoice_item_ids))
        ):
            raise ValueError(
                "The same invoice item cannot "
                "appear more than once"
            )

        return self


class ReturnInspectionRequest(BaseModel):
    inspection_notes: str = Field(
        min_length=3,
        max_length=5000,
    )

    @field_validator("inspection_notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Inspection notes must contain "
                "at least 3 characters"
            )

        return value


class ReturnApprovalRequest(BaseModel):
    approved: bool

    resolution: ReturnResolution = (
        ReturnResolution.PENDING
    )

    approval_notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    refund_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    @field_validator("approval_notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)

    @model_validator(mode="after")
    def validate_resolution(
        self,
    ) -> "ReturnApprovalRequest":
        if self.approved:
            if self.resolution in {
                ReturnResolution.PENDING,
                ReturnResolution.REJECTED,
            }:
                raise ValueError(
                    "Approved return requires "
                    "a valid resolution"
                )

            if (
                self.resolution
                != ReturnResolution.REFUND
                and self.refund_amount
                > Decimal("0.00")
            ):
                raise ValueError(
                    "Refund amount is only allowed "
                    "for refund resolution"
                )

        else:
            if self.resolution not in {
                ReturnResolution.PENDING,
                ReturnResolution.REJECTED,
            }:
                raise ValueError(
                    "Rejected return cannot have "
                    "an approved resolution"
                )

            if self.refund_amount > Decimal("0.00"):
                raise ValueError(
                    "Rejected return cannot have "
                    "a refund amount"
                )

        return self


class ReturnStatusChangeRequest(BaseModel):
    new_status: ReturnStatus

    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("remarks")
    @classmethod
    def normalize_remarks(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ReplacementItemRequest(BaseModel):
    return_item_id: int = Field(
        ge=1
    )

    replacement_product_id: int = Field(
        ge=1
    )

    replacement_serial_number_id: int | None = Field(
        default=None,
        ge=1,
    )

    warehouse_id: int = Field(
        ge=1
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
        return clean_optional_text(value)


class SalesReturnStatusHistoryResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    return_id: int
    old_status: str | None
    new_status: str
    remarks: str | None
    changed_by_id: int
    created_at: datetime


class SalesReturnItemResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    return_id: int

    invoice_item_id: int

    product_id: int | None
    serial_number_id: int | None

    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    condition: str
    reason: str | None

    destination_warehouse_id: int | None
    stock_movement_id: int | None

    replacement_product_id: int | None
    replacement_serial_number_id: int | None
    replacement_stock_movement_id: int | None

    notes: str | None

    created_at: datetime


class SalesReturnResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    company_id: int
    branch_id: int

    return_number: str

    invoice_id: int
    customer_id: int

    return_type: str
    status: str
    resolution: str

    reason: str

    inspection_notes: str | None
    approval_notes: str | None

    subtotal: Decimal
    refund_amount: Decimal

    approved_by_id: int | None
    approved_at: datetime | None
    completed_at: datetime | None

    created_by_id: int
    updated_by_id: int | None

    created_at: datetime
    updated_at: datetime


class SalesReturnDetailResponse(
    SalesReturnResponse
):
    invoice_number: str
    customer_name: str
    customer_phone: str

    items: list[
        SalesReturnItemResponse
    ]

    status_history: list[
        SalesReturnStatusHistoryResponse
    ]


class SalesReturnListResponse(BaseModel):
    items: list[
        SalesReturnDetailResponse
    ]

    total: int
    page: int
    page_size: int
    total_pages: int
