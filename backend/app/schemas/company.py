from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    name: str
    phone: str | None
    address: str | None
    is_main_branch: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str | None
    registration_number: str | None
    tax_number: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    logo_path: str | None
    currency_code: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    branches: list[BranchResponse] = []


class CompanyUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    legal_name: str | None = Field(
        default=None,
        max_length=200,
    )
    registration_number: str | None = Field(
        default=None,
        max_length=100,
    )
    tax_number: str | None = Field(
        default=None,
        max_length=100,
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    email: str | None = Field(
        default=None,
        max_length=255,
    )
    address: str | None = None
    city: str | None = Field(
        default=None,
        max_length=100,
    )
    logo_path: str | None = Field(
        default=None,
        max_length=500,
    )
    currency_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )
    timezone: str | None = Field(
        default=None,
        max_length=100,
    )


class BranchUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    address: str | None = None
    is_active: bool | None = None
