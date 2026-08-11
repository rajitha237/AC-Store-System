from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.customer import (
    CreditStatus,
    CustomerStatus,
    CustomerType,
)


def normalize_optional_text(value: str | None) -> str | None:
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
        raise ValueError("Phone number must contain digits only")

    if len(normalized) != 10:
        raise ValueError(
            "Sri Lankan phone number must contain 10 digits"
        )

    return normalized


class CustomerBase(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=180,
    )

    business_name: str | None = Field(
        default=None,
        max_length=200,
    )

    customer_type: CustomerType = CustomerType.CASH

    nic_number: str | None = Field(
        default=None,
        max_length=20,
    )

    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )

    primary_phone: str = Field(
        min_length=9,
        max_length=20,
    )

    secondary_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    sms_phone: str | None = Field(
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

    district: str | None = Field(
        default=None,
        max_length=100,
    )

    province: str | None = Field(
        default=None,
        max_length=100,
    )

    postal_code: str | None = Field(
        default=None,
        max_length=20,
    )

    credit_status: CreditStatus = CreditStatus.RESTRICTED

    credit_limit: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    sms_allowed: bool = True

    notes: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError("Full name is required")

        return normalized

    @field_validator(
        "business_name",
        "registration_number",
        "address_line_1",
        "address_line_2",
        "city",
        "district",
        "province",
        "postal_code",
        "notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @field_validator("nic_number")
    @classmethod
    def validate_nic(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_optional_text(value)

        if normalized is None:
            return None

        normalized = normalized.upper().replace(" ", "")

        if len(normalized) not in {10, 12}:
            raise ValueError(
                "NIC number must contain 10 or 12 characters"
            )

        if len(normalized) == 10:
            if not (
                normalized[:9].isdigit()
                and normalized[-1] in {"V", "X"}
            ):
                raise ValueError(
                    "Old NIC format is invalid"
                )
        elif not normalized.isdigit():
            raise ValueError(
                "New NIC format must contain digits only"
            )

        return normalized

    @field_validator("primary_phone")
    @classmethod
    def validate_primary_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("secondary_phone", "sms_phone")
    @classmethod
    def validate_optional_phone(
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


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=180,
    )

    business_name: str | None = Field(
        default=None,
        max_length=200,
    )

    customer_type: CustomerType | None = None
    status: CustomerStatus | None = None

    nic_number: str | None = Field(
        default=None,
        max_length=20,
    )

    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )

    primary_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    secondary_phone: str | None = Field(
        default=None,
        max_length=20,
    )

    sms_phone: str | None = Field(
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

    district: str | None = Field(
        default=None,
        max_length=100,
    )

    province: str | None = Field(
        default=None,
        max_length=100,
    )

    postal_code: str | None = Field(
        default=None,
        max_length=20,
    )

    credit_status: CreditStatus | None = None

    credit_limit: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    sms_allowed: bool | None = None
    notes: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError("Full name is required")

        return normalized

    @field_validator(
        "business_name",
        "registration_number",
        "address_line_1",
        "address_line_2",
        "city",
        "district",
        "province",
        "postal_code",
        "notes",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(value)

    @field_validator("nic_number")
    @classmethod
    def validate_nic(
        cls,
        value: str | None,
    ) -> str | None:
        normalized = normalize_optional_text(value)

        if normalized is None:
            return None

        normalized = normalized.upper().replace(" ", "")

        if len(normalized) not in {10, 12}:
            raise ValueError(
                "NIC number must contain 10 or 12 characters"
            )

        if len(normalized) == 10:
            if not (
                normalized[:9].isdigit()
                and normalized[-1] in {"V", "X"}
            ):
                raise ValueError("Old NIC format is invalid")
        elif not normalized.isdigit():
            raise ValueError(
                "New NIC format must contain digits only"
            )

        return normalized

    @field_validator(
        "primary_phone",
        "secondary_phone",
        "sms_phone",
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


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    customer_number: str
    customer_type: str
    status: str
    full_name: str
    business_name: str | None
    nic_number: str | None
    registration_number: str | None
    primary_phone: str
    secondary_phone: str | None
    sms_phone: str
    email: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    district: str | None
    province: str | None
    postal_code: str | None
    credit_status: str
    credit_limit: Decimal
    current_balance: Decimal
    sms_allowed: bool
    notes: str | None
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
