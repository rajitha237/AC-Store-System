from datetime import date, time
from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.service import (
    ApprovalStatus,
    ServiceJobPriority,
    ServiceJobStatus,
    ServiceType,
)


def clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


class ServiceJobCreate(BaseModel):
    customer_id: int = Field(ge=1)
    branch_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    sold_serial_id: int | None = Field(default=None, ge=1)

    serial_number: str | None = Field(default=None, max_length=150)
    secondary_serial_number: str | None = Field(default=None, max_length=150)
    brand_name: str | None = Field(default=None, max_length=120)
    model_number: str | None = Field(default=None, max_length=120)
    item_color: str | None = Field(default=None, max_length=80)

    service_type: ServiceType = ServiceType.REPAIR
    priority: ServiceJobPriority = ServiceJobPriority.NORMAL

    complaint: str = Field(min_length=3, max_length=5000)

    reported_issue: str | None = None
    accessories_received: str | None = None
    physical_condition: str | None = None
    special_notes: str | None = None

    technician_id: int | None = Field(default=None, ge=1)
    receiving_officer_id: int | None = Field(default=None, ge=1)

    is_warranty_job: bool = False
    related_invoice_id: int | None = Field(default=None, ge=1)

    expected_completion_date: date | None = None
    scheduled_visit_date: date | None = None

    estimated_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    @field_validator(
        "serial_number",
        "secondary_serial_number",
        "brand_name",
        "model_number",
        "item_color",
        "reported_issue",
        "accessories_received",
        "physical_condition",
        "special_notes",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)

    @field_validator("complaint")
    @classmethod
    def normalize_complaint(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Complaint must contain at least 3 characters"
            )

        return value


class ServiceJobUpdate(BaseModel):
    technician_id: int | None = Field(default=None, ge=1)
    expected_completion_date: date | None = None
    scheduled_visit_date: date | None = None

    reported_issue: str | None = None
    technician_diagnosis: str | None = None
    work_performed: str | None = None
    testing_result: str | None = None
    accessories_received: str | None = None
    physical_condition: str | None = None
    special_notes: str | None = None
    warranty_notes: str | None = None

    estimated_cost: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    discount_amount: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    @field_validator(
        "reported_issue",
        "technician_diagnosis",
        "work_performed",
        "testing_result",
        "accessories_received",
        "physical_condition",
        "special_notes",
        "warranty_notes",
    )
    @classmethod
    def normalize_text(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ServiceStatusChangeRequest(BaseModel):
    new_status: ServiceJobStatus
    remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("remarks")
    @classmethod
    def normalize_remarks(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ServiceApprovalRequest(BaseModel):
    approval_status: ApprovalStatus
    remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("remarks")
    @classmethod
    def normalize_remarks(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ServicePartCreate(BaseModel):
    product_id: int = Field(ge=1)
    warehouse_id: int = Field(ge=1)

    quantity: Decimal = Field(
        gt=Decimal("0.000"),
        max_digits=18,
        decimal_places=3,
    )

    unit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ServicePartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_card_id: int
    product_id: int
    warehouse_id: int
    quantity: Decimal
    unit_cost: Decimal
    unit_price: Decimal
    line_total: Decimal
    stock_movement_id: int | None
    notes: str | None
    created_by_id: int
    created_at: datetime


class ServiceLabourCreate(BaseModel):
    description: str = Field(min_length=2, max_length=500)

    hours: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
    )

    amount: Decimal = Field(
        ge=Decimal("0.00"),
        max_digits=18,
        decimal_places=2,
    )

    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("description")
    @classmethod
    def normalize_description(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Description is required")

        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(
        cls,
        value: str | None,
    ) -> str | None:
        return clean_optional_text(value)


class ServiceLabourResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_card_id: int
    description: str
    hours: Decimal
    amount: Decimal
    notes: str | None
    created_by_id: int
    created_at: datetime


class ServiceJobStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_card_id: int
    old_status: str | None
    new_status: str
    remarks: str | None
    changed_by_id: int
    created_at: datetime


class ServiceJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    branch_id: int
    job_number: str
    customer_id: int

    product_id: int | None
    sold_serial_id: int | None

    serial_number: str | None
    secondary_serial_number: str | None
    brand_name: str | None
    model_number: str | None
    item_color: str | None

    service_type: str
    priority: str
    status: str
    approval_status: str

    complaint: str
    reported_issue: str | None
    technician_diagnosis: str | None
    work_performed: str | None
    testing_result: str | None

    accessories_received: str | None
    physical_condition: str | None
    special_notes: str | None

    technician_id: int | None
    receiving_officer_id: int | None

    is_warranty_job: bool
    warranty_verified: bool
    warranty_notes: str | None
    related_invoice_id: int | None

    estimated_cost: Decimal
    labour_total: Decimal
    parts_total: Decimal
    discount_amount: Decimal
    final_amount: Decimal

    received_at: datetime
    expected_completion_date: date | None
    scheduled_visit_date: date | None
    approval_at: datetime | None
    completed_at: datetime | None
    delivered_at: datetime | None

    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime


class ServiceJobDetailResponse(ServiceJobResponse):
    customer_name: str
    customer_phone: str

    product_name: str | None
    product_code: str | None

    technician_name: str | None
    receiving_officer_name: str | None

    status_history: list[ServiceJobStatusHistoryResponse]
    parts: list[ServicePartResponse]
    labour_items: list[ServiceLabourResponse]


class ServiceJobListResponse(BaseModel):
    items: list[ServiceJobDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int



# ===== LEGACY SERVICE JOB HISTORY API =====

class LegacyServiceJobLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_number: int
    legacy_code: str | None = None
    name: str | None = None
    line_type: str

    quantity: Decimal
    rate: Decimal
    discount: Decimal
    discount_value: Decimal
    line_total: Decimal

    unit: str | None = None
    serial_no: str | None = None


class LegacyServiceJobListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    legacy_job_id: int
    invoice_code: str | None = None

    job_date: date
    job_time: time | None = None

    reference_no: str | None = None
    sale_type: str | None = None

    legacy_customer_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None

    source_total: Decimal
    net_amount: Decimal
    pay_amount: Decimal
    rest_amount: Decimal

    cash_amount: Decimal
    credit_amount: Decimal
    cheque_amount: Decimal
    card_amount: Decimal
    bank_amount: Decimal

    is_cancelled: bool

    legacy_user_id: int | None = None
    legacy_user_name: str | None = None

    legacy_service_date: date | None = None
    legacy_warranty_period: str | None = None

    management_status: str = "received"
    status_remarks: str | None = None
    status_updated_at: datetime | None = None
    status_updated_by_id: int | None = None


class LegacyAdditionalSaleItemResponse(BaseModel):
    product_id: int | None = None
    product_code: str | None = None
    product_name: str | None = None
    warehouse_id: int | None = None
    warehouse_code: str | None = None
    warehouse_name: str | None = None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class LegacyAdditionalSaleResponse(BaseModel):
    id: int
    invoice_number: str
    grand_total: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    payment_status: str
    invoice_status: str
    created_at: datetime
    items: list[LegacyAdditionalSaleItemResponse]


class LegacyServiceJobDetailResponse(
    LegacyServiceJobListItemResponse
):
    bill_discount: Decimal
    bill_discount_value: Decimal

    gross_amount: Decimal
    profit: Decimal

    over_balance_amount: Decimal
    balance_amount: Decimal

    migration_notes: str | None = None

    lines: list[LegacyServiceJobLineResponse]
    additional_sales: list[LegacyAdditionalSaleResponse]


class LegacyServiceJobStatusUpdateRequest(BaseModel):
    status: str
    remarks: str | None = None


class LegacyServiceJobStatusUpdateResponse(BaseModel):
    legacy_job_id: int
    management_status: str
    status_remarks: str | None = None
    status_updated_at: datetime
    status_updated_by_id: int | None = None



class LegacyServiceJobHistoryListResponse(BaseModel):
    items: list[LegacyServiceJobListItemResponse]

    total: int
    page: int
    page_size: int
    pages: int
