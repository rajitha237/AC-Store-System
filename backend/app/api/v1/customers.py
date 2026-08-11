from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    CurrentUser,
    DatabaseSession,
    require_permission,
)
from app.models import CustomerStatus, CustomerType, User
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer import (
    create_customer,
    get_customer_or_404,
    list_customers,
    update_customer,
)

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)

CanViewCustomers = Annotated[
    User,
    Depends(require_permission("customers.view")),
]

CanCreateCustomers = Annotated[
    User,
    Depends(require_permission("customers.create")),
]

CanUpdateCustomers = Annotated[
    User,
    Depends(require_permission("customers.update")),
]


@router.get(
    "",
    response_model=CustomerListResponse,
)
async def read_customers(
    session: DatabaseSession,
    _: CanViewCustomers,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    customer_type: CustomerType | None = None,
    customer_status: CustomerStatus | None = None,
) -> CustomerListResponse:
    return await list_customers(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        customer_type=(
            customer_type.value
            if customer_type is not None
            else None
        ),
        customer_status=(
            customer_status.value
            if customer_status is not None
            else None
        ),
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_customer_record(
    payload: CustomerCreate,
    session: DatabaseSession,
    current_user: CanCreateCustomers,
) -> CustomerResponse:
    customer = await create_customer(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
async def read_customer(
    customer_id: int,
    session: DatabaseSession,
    _: CanViewCustomers,
) -> CustomerResponse:
    customer = await get_customer_or_404(
        session=session,
        customer_id=customer_id,
    )

    return CustomerResponse.model_validate(customer)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
)
async def update_customer_record(
    customer_id: int,
    payload: CustomerUpdate,
    session: DatabaseSession,
    current_user: CanUpdateCustomers,
) -> CustomerResponse:
    customer = await get_customer_or_404(
        session=session,
        customer_id=customer_id,
    )

    updated_customer = await update_customer(
        session=session,
        customer=customer,
        payload=payload,
        current_user=current_user,
    )

    return CustomerResponse.model_validate(
        updated_customer
    )


@router.delete(
    "/{customer_id}",
    response_model=CustomerResponse,
)
async def deactivate_customer(
    customer_id: int,
    session: DatabaseSession,
    current_user: CanUpdateCustomers,
) -> CustomerResponse:
    customer = await get_customer_or_404(
        session=session,
        customer_id=customer_id,
    )

    payload = CustomerUpdate(
        status=CustomerStatus.INACTIVE,
    )

    updated_customer = await update_customer(
        session=session,
        customer=customer,
        payload=payload,
        current_user=current_user,
    )

    return CustomerResponse.model_validate(
        updated_customer
    )
