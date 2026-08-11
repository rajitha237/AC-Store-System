from __future__ import annotations

from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Customer, User
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)


async def get_default_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(Company.is_active.is_(True))
        .order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active company record is not configured",
        )

    return company


async def validate_customer_duplicates(
    session: AsyncSession,
    company_id: int,
    *,
    nic_number: str | None,
    primary_phone: str | None,
    email: str | None,
    exclude_customer_id: int | None = None,
) -> None:
    conditions = []

    if nic_number:
        conditions.append(Customer.nic_number == nic_number)

    if primary_phone:
        conditions.append(
            Customer.primary_phone == primary_phone
        )

    if email:
        conditions.append(Customer.email == email)

    if not conditions:
        return

    statement = select(Customer).where(
        Customer.company_id == company_id,
        or_(*conditions),
    )

    if exclude_customer_id is not None:
        statement = statement.where(
            Customer.id != exclude_customer_id
        )

    result = await session.execute(statement)
    duplicate_customers = result.scalars().all()

    for customer in duplicate_customers:
        if (
            nic_number
            and customer.nic_number == nic_number
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A customer with this NIC number "
                    "already exists"
                ),
            )

        if (
            primary_phone
            and customer.primary_phone == primary_phone
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A customer with this primary phone "
                    "number already exists"
                ),
            )

        if email and customer.email == email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A customer with this email address "
                    "already exists"
                ),
            )


async def create_customer(
    session: AsyncSession,
    payload: CustomerCreate,
    current_user: User,
) -> Customer:
    company = await get_default_company(session)

    sms_phone = payload.sms_phone or payload.primary_phone

    await validate_customer_duplicates(
        session=session,
        company_id=company.id,
        nic_number=payload.nic_number,
        primary_phone=payload.primary_phone,
        email=payload.email,
    )

    customer = Customer(
        company_id=company.id,
        customer_number=None,
        customer_type=payload.customer_type.value,
        full_name=payload.full_name,
        business_name=payload.business_name,
        nic_number=payload.nic_number,
        registration_number=payload.registration_number,
        primary_phone=payload.primary_phone,
        secondary_phone=payload.secondary_phone,
        sms_phone=sms_phone,
        email=payload.email,
        address_line_1=payload.address_line_1,
        address_line_2=payload.address_line_2,
        city=payload.city,
        district=payload.district,
        province=payload.province,
        postal_code=payload.postal_code,
        credit_status=payload.credit_status.value,
        credit_limit=payload.credit_limit,
        sms_allowed=payload.sms_allowed,
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(customer)

    try:
        await session.flush()

        customer.customer_number = f"CUS-{customer.id:06d}"

        await session.commit()
        await session.refresh(customer)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Customer could not be created because "
                "a unique value already exists"
            ),
        ) from exc

    return customer


async def list_customers(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    customer_type: str | None,
    customer_status: str | None,
) -> CustomerListResponse:
    filters = []

    if search:
        normalized_search = search.strip()

        if normalized_search:
            pattern = f"%{normalized_search}%"

            filters.append(
                or_(
                    Customer.customer_number.ilike(pattern),
                    Customer.full_name.ilike(pattern),
                    Customer.business_name.ilike(pattern),
                    Customer.nic_number.ilike(pattern),
                    Customer.primary_phone.ilike(pattern),
                    Customer.sms_phone.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )

    if customer_type:
        filters.append(
            Customer.customer_type == customer_type
        )

    if customer_status:
        filters.append(Customer.status == customer_status)

    count_statement = (
        select(func.count())
        .select_from(Customer)
        .where(*filters)
    )

    total = int(
        await session.scalar(count_statement) or 0
    )

    offset = (page - 1) * page_size

    statement = (
        select(Customer)
        .where(*filters)
        .order_by(
            Customer.created_at.desc(),
            Customer.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await session.execute(statement)
    customers = result.scalars().all()

    return CustomerListResponse(
        items=[
            CustomerResponse.model_validate(customer)
            for customer in customers
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


async def get_customer_or_404(
    session: AsyncSession,
    customer_id: int,
) -> Customer:
    customer = await session.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer record was not found",
        )

    return customer


async def update_customer(
    session: AsyncSession,
    customer: Customer,
    payload: CustomerUpdate,
    current_user: User,
) -> Customer:
    update_data = payload.model_dump(exclude_unset=True)

    nic_number = update_data.get(
        "nic_number",
        customer.nic_number,
    )
    primary_phone = update_data.get(
        "primary_phone",
        customer.primary_phone,
    )
    email = update_data.get(
        "email",
        customer.email,
    )

    await validate_customer_duplicates(
        session=session,
        company_id=customer.company_id,
        nic_number=nic_number,
        primary_phone=primary_phone,
        email=email,
        exclude_customer_id=customer.id,
    )

    for field_name, value in update_data.items():
        if hasattr(value, "value"):
            value = value.value

        setattr(customer, field_name, value)

    if (
        "primary_phone" in update_data
        and "sms_phone" not in update_data
        and customer.sms_phone is None
    ):
        customer.sms_phone = customer.primary_phone

    if not customer.sms_phone:
        customer.sms_phone = customer.primary_phone

    customer.updated_by_id = current_user.id

    try:
        await session.commit()
        await session.refresh(customer)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Customer could not be updated because "
                "a unique value already exists"
            ),
        ) from exc

    return customer
