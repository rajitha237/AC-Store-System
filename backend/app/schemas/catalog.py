from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProductType(str, Enum):
    EQUIPMENT = "equipment"
    SPARE_PART = "spare_part"
    INSTALLATION_MATERIAL = "installation_material"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    SERVICE_ITEM = "service_item"


def normalize_required_text(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError("This field is required")

    return normalized


def normalize_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def normalize_code(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "-")

    if not normalized:
        raise ValueError("Code is required")

    valid_characters = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )

    if any(
        character not in valid_characters
        for character in normalized
    ):
        raise ValueError(
            "Code can contain letters, numbers, "
            "hyphens and underscores only"
        )

    return normalized


class CategoryCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=30,
    )

    name: str = Field(
        min_length=2,
        max_length=150,
    )

    parent_id: int | None = Field(
        default=None,
        ge=1,
    )

    description: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return normalize_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class CategoryUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    parent_id: int | None = Field(
        default=None,
        ge=1,
    )

    description: str | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def validate_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_required_text(value)

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    parent_id: int | None
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=30,
    )

    name: str = Field(
        min_length=2,
        max_length=150,
    )

    description: str | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return normalize_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class BrandUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=30,
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    description: str | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def validate_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_required_text(value)

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    decimal_places: int
    is_active: bool


class ProductCreate(BaseModel):
    barcode: str | None = Field(
        default=None,
        max_length=100,
    )

    category_id: int = Field(ge=1)
    brand_id: int | None = Field(default=None, ge=1)
    unit_id: int = Field(ge=1)

    name: str = Field(
        min_length=2,
        max_length=200,
    )

    model_number: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str | None = None

    btu_capacity: int | None = Field(
        default=None,
        ge=0,
        le=1000000,
    )

    product_type: ProductType = ProductType.EQUIPMENT

    track_serial_numbers: bool = False

    purchase_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    selling_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    minimum_selling_price: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    warranty_months: int = Field(
        default=0,
        ge=0,
        le=120,
    )

    reorder_level: Decimal = Field(
        default=Decimal("0.000"),
        ge=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    reorder_quantity: Decimal = Field(
        default=Decimal("0.000"),
        ge=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    image_path: str | None = Field(
        default=None,
        max_length=500,
    )

    technical_notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator(
        "barcode",
        "model_number",
        "description",
        "image_path",
        "technical_notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_prices(self) -> "ProductCreate":
        if self.minimum_selling_price > self.selling_price:
            raise ValueError(
                "Minimum selling price cannot be greater "
                "than selling price"
            )

        return self


class ProductUpdate(BaseModel):
    barcode: str | None = Field(
        default=None,
        max_length=100,
    )

    category_id: int | None = Field(
        default=None,
        ge=1,
    )

    brand_id: int | None = Field(
        default=None,
        ge=1,
    )

    unit_id: int | None = Field(
        default=None,
        ge=1,
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    model_number: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str | None = None

    btu_capacity: int | None = Field(
        default=None,
        ge=0,
        le=1000000,
    )

    product_type: ProductType | None = None
    track_serial_numbers: bool | None = None

    purchase_cost: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    selling_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    minimum_selling_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    warranty_months: int | None = Field(
        default=None,
        ge=0,
        le=120,
    )

    reorder_level: Decimal | None = Field(
        default=None,
        ge=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    reorder_quantity: Decimal | None = Field(
        default=None,
        ge=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    image_path: str | None = Field(
        default=None,
        max_length=500,
    )

    technical_notes: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return normalize_required_text(value)

    @field_validator(
        "barcode",
        "model_number",
        "description",
        "image_path",
        "technical_notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_code: str
    barcode: str | None
    category_id: int
    brand_id: int | None
    unit_id: int
    name: str
    model_number: str | None
    description: str | None
    btu_capacity: int | None
    product_type: str
    track_serial_numbers: bool
    purchase_cost: Decimal
    selling_price: Decimal
    minimum_selling_price: Decimal
    warranty_months: int
    reorder_level: Decimal
    reorder_quantity: Decimal
    image_path: str | None
    technical_notes: str | None
    is_active: bool
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime

    category: CategoryResponse
    brand: BrandResponse | None
    unit: UnitResponse


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
