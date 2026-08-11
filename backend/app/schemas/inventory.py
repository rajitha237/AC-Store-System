from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class InventoryIssueType(str, Enum):
    SALE = "sale"
    SERVICE = "service"
    INTERNAL_USE = "internal_use"
    REPLACEMENT = "replacement"


def normalize_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def normalize_serial_number(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "")

    if len(normalized) < 3:
        raise ValueError(
            "Serial number must contain at least 3 characters"
        )

    if len(normalized) > 150:
        raise ValueError(
            "Serial number cannot exceed 150 characters"
        )

    return normalized


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    code: str
    name: str
    warehouse_type: str
    is_active: bool
    created_at: datetime


class SerializedUnitInput(BaseModel):
    serial_number: str = Field(
        min_length=3,
        max_length=150,
    )

    secondary_serial_number: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = None

    @field_validator("serial_number")
    @classmethod
    def validate_serial_number(
        cls,
        value: str,
    ) -> str:
        return normalize_serial_number(value)

    @field_validator("secondary_serial_number")
    @classmethod
    def validate_secondary_serial_number(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None or not value.strip():
            return None

        return normalize_serial_number(value)

    @field_validator("notes")
    @classmethod
    def validate_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class SerializedStockReceiveRequest(BaseModel):
    product_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)

    supplier_id: int | None = Field(
        default=None,
        ge=1,
    )

    unit_cost: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    reference_type: str = Field(
        default="opening_balance",
        min_length=2,
        max_length=80,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    notes: str | None = None

    serials: list[SerializedUnitInput] = Field(
        min_length=1,
        max_length=500,
    )

    @field_validator(
        "reference_type",
        "reference_id",
        "notes",
    )
    @classmethod
    def validate_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @field_validator("serials")
    @classmethod
    def validate_unique_serials(
        cls,
        serials: list[SerializedUnitInput],
    ) -> list[SerializedUnitInput]:
        primary_serials = [
            item.serial_number
            for item in serials
        ]

        if len(primary_serials) != len(set(primary_serials)):
            raise ValueError(
                "Duplicate primary serial numbers exist "
                "inside the request"
            )

        secondary_serials = [
            item.secondary_serial_number
            for item in serials
            if item.secondary_serial_number is not None
        ]

        if len(secondary_serials) != len(
            set(secondary_serials)
        ):
            raise ValueError(
                "Duplicate secondary serial numbers exist "
                "inside the request"
            )

        primary_set = set(primary_serials)

        for secondary_serial in secondary_serials:
            if secondary_serial in primary_set:
                raise ValueError(
                    "A secondary serial number cannot also "
                    "be used as a primary serial number"
                )

        return serials


class NonSerializedStockReceiveRequest(BaseModel):
    product_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)

    supplier_id: int | None = Field(
        default=None,
        ge=1,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    unit_cost: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    reference_type: str = Field(
        default="opening_balance",
        min_length=2,
        max_length=80,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    notes: str | None = None

    @field_validator(
        "reference_type",
        "reference_id",
        "notes",
    )
    @classmethod
    def validate_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class SerializedStockIssueRequest(BaseModel):
    serial_number_id: int = Field(ge=1)
    customer_id: int = Field(ge=1)

    issue_type: InventoryIssueType = (
        InventoryIssueType.SALE
    )

    reference_type: str = Field(
        default="sale",
        min_length=2,
        max_length=80,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    warranty_start_date: date | None = None
    notes: str | None = None

    @field_validator(
        "reference_type",
        "reference_id",
        "notes",
    )
    @classmethod
    def validate_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class NonSerializedStockIssueRequest(BaseModel):
    product_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)

    customer_id: int | None = Field(
        default=None,
        ge=1,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    issue_type: InventoryIssueType = (
        InventoryIssueType.SALE
    )

    reference_type: str = Field(
        default="sale",
        min_length=2,
        max_length=80,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    notes: str | None = None

    @field_validator(
        "reference_type",
        "reference_id",
        "notes",
    )
    @classmethod
    def validate_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class SerialNumberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_id: int
    serial_number: str
    secondary_serial_number: str | None
    warehouse_id: int | None
    supplier_id: int | None
    status: str
    current_customer_id: int | None
    warranty_start_date: date | None
    warranty_end_date: date | None
    received_at: datetime | None
    sold_at: datetime | None
    notes: str | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class SerialNumberDetailResponse(
    SerialNumberResponse
):
    product_code: str
    product_name: str
    model_number: str | None
    warehouse_code: str | None
    warehouse_name: str | None
    supplier_name: str | None
    customer_name: str | None
    customer_phone: str | None


class StockBalanceResponse(BaseModel):
    id: int
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    product_id: int
    product_code: str
    product_name: str
    track_serial_numbers: bool
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    average_cost: Decimal
    reorder_level: Decimal
    is_low_stock: bool


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    branch_id: int
    warehouse_id: int
    product_id: int
    serial_number_id: int | None
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    reference_type: str | None
    reference_id: str | None
    movement_date: datetime
    notes: str | None
    created_by_id: int
    created_at: datetime


class SerializedStockReceiveResponse(BaseModel):
    message: str
    product_id: int
    warehouse_id: int
    quantity_received: int
    quantity_on_hand: Decimal
    average_cost: Decimal
    serials: list[SerialNumberResponse]


class NonSerializedStockReceiveResponse(BaseModel):
    message: str
    product_id: int
    warehouse_id: int
    quantity_received: Decimal
    quantity_on_hand: Decimal
    quantity_available: Decimal
    average_cost: Decimal
    movement: StockMovementResponse


class SerializedStockIssueResponse(BaseModel):
    message: str
    product_id: int
    warehouse_id: int
    customer_id: int
    quantity_issued: Decimal
    quantity_on_hand: Decimal
    serial: SerialNumberDetailResponse
    movement: StockMovementResponse


class NonSerializedStockIssueResponse(BaseModel):
    message: str
    product_id: int
    warehouse_id: int
    customer_id: int | None
    quantity_issued: Decimal
    quantity_on_hand: Decimal
    quantity_available: Decimal
    average_cost: Decimal
    movement: StockMovementResponse


class StockMovementListResponse(BaseModel):
    items: list[StockMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


from enum import Enum as _InventoryAdjustmentEnum


class StockAdjustmentDirection(
    str,
    _InventoryAdjustmentEnum,
):
    INCREASE = "increase"
    DECREASE = "decrease"


class StockAdjustmentRequest(BaseModel):
    product_id: int = Field(
        ge=1,
    )

    warehouse_id: int = Field(
        ge=1,
    )

    direction: StockAdjustmentDirection

    quantity: Decimal = Field(
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=3,
    )

    unit_cost: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=18,
        decimal_places=2,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    reason: str = Field(
        min_length=3,
        max_length=250,
    )

    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class StockAdjustmentResponse(BaseModel):
    message: str
    product_id: int
    warehouse_id: int
    direction: StockAdjustmentDirection
    quantity_adjusted: Decimal
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    average_cost: Decimal
    movement: StockMovementResponse


class NonSerializedStockTransferRequest(BaseModel):
    product_id: int = Field(
        ge=1,
    )

    source_warehouse_id: int = Field(
        ge=1,
    )

    destination_warehouse_id: int = Field(
        ge=1,
    )

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    reason: str = Field(
        min_length=3,
        max_length=250,
    )

    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class NonSerializedStockTransferResponse(BaseModel):
    message: str

    product_id: int

    source_warehouse_id: int
    destination_warehouse_id: int

    quantity_transferred: Decimal

    source_quantity_on_hand: Decimal
    source_quantity_reserved: Decimal
    source_quantity_available: Decimal

    destination_quantity_on_hand: Decimal
    destination_quantity_reserved: Decimal
    destination_quantity_available: Decimal

    destination_average_cost: Decimal

    transfer_out_movement: StockMovementResponse

    transfer_in_movement: StockMovementResponse


class SerializedStockTransferRequest(BaseModel):
    product_id: int = Field(
        ge=1,
    )

    source_warehouse_id: int = Field(
        ge=1,
    )

    destination_warehouse_id: int = Field(
        ge=1,
    )

    serial_number_ids: list[int] = Field(
        min_length=1,
        max_length=500,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )

    reason: str = Field(
        min_length=3,
        max_length=250,
    )

    notes: str | None = Field(
        default=None,
        max_length=1000,
    )


class SerializedStockTransferResponse(BaseModel):
    message: str

    product_id: int

    source_warehouse_id: int
    destination_warehouse_id: int

    quantity_transferred: Decimal

    source_quantity_on_hand: Decimal
    destination_quantity_on_hand: Decimal

    serials: list[SerialNumberResponse]

    transfer_out_movements: list[StockMovementResponse]

    transfer_in_movements: list[StockMovementResponse]
