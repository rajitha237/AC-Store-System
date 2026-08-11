from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


def normalize_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def normalize_phone(value: str) -> str:
    normalized = (
        value.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if normalized.startswith("+94"):
        normalized = "0" + normalized[3:]

    if not normalized.isdigit():
        raise ValueError(
            "Phone number must contain digits only"
        )

    if len(normalized) != 10:
        raise ValueError(
            "Sri Lankan phone number must contain 10 digits"
        )

    return normalized


class SupplierBase(BaseModel):
    company_name: str = Field(
        min_length=2,
        max_length=200,
    )

    contact_person: str | None = Field(
        default=None,
        max_length=150,
    )

    phone: str = Field(
        min_length=9,
        max_length=20,
    )

    secondary_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    address_line_1: str | None = Field(
        default=None,
        max_length=255,
    )

    address_line_2: str | None = Field(
        default=None,
        max_length=255,
    )

    city: str | None = Field(
        default=None,
        max_length=100,
    )

    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )

    tax_number: str | None = Field(
        default=None,
        max_length=100,
    )

    credit_limit: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    payment_terms_days: int = Field(
        default=0,
        ge=0,
        le=365,
    )

    notes: str | None = None

    @field_validator("company_name")
    @classmethod
    def validate_company_name(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Supplier company name is required"
            )

        return normalized

    @field_validator(
        "contact_person",
        "address_line_1",
        "address_line_2",
        "city",
        "registration_number",
        "tax_number",
        "notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str,
    ) -> str:
        return normalize_phone(value)

    @field_validator("secondary_phone")
    @classmethod
    def validate_secondary_phone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None or not value.strip():
            return None

        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def validate_email(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_optional_text(value)

        if normalized is None:
            return None

        normalized = normalized.lower()

        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("Email address is invalid")

        return normalized


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    company_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    contact_person: str | None = Field(
        default=None,
        max_length=150,
    )

    phone: str | None = Field(
        default=None,
        max_length=20,
    )

    secondary_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    address_line_1: str | None = Field(
        default=None,
        max_length=255,
    )

    address_line_2: str | None = Field(
        default=None,
        max_length=255,
    )

    city: str | None = Field(
        default=None,
        max_length=100,
    )

    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )

    tax_number: str | None = Field(
        default=None,
        max_length=100,
    )

    credit_limit: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    payment_terms_days: int | None = Field(
        default=None,
        ge=0,
        le=365,
    )

    notes: str | None = None
    is_active: bool | None = None

    @field_validator("company_name")
    @classmethod
    def validate_company_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError(
                "Supplier company name is required"
            )

        return normalized

    @field_validator(
        "contact_person",
        "address_line_1",
        "address_line_2",
        "city",
        "registration_number",
        "tax_number",
        "notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @field_validator(
        "phone",
        "secondary_phone",
    )
    @classmethod
    def validate_phone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None or not value.strip():
            return None

        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def validate_email(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_optional_text(value)

        if normalized is None:
            return None

        normalized = normalized.lower()

        if (
            "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
        ):
            raise ValueError("Email address is invalid")

        return normalized


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    supplier_code: str
    company_name: str
    contact_person: str | None
    phone: str
    secondary_phone: str | None
    email: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    registration_number: str | None
    tax_number: str | None
    credit_limit: Decimal
    payment_terms_days: int
    current_payable: Decimal
    notes: str | None
    is_active: bool
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
