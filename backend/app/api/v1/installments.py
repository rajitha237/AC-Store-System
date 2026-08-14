from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.installment import (
    CustomerLedgerResponse,
    CustomerStatementResponse,
    InstallmentPaymentCreate,
    InstallmentPaymentResponse,
    InstallmentPaymentReverse,
    InstallmentPlanCancel,
    InstallmentPlanCreate,
    InstallmentPlanDetailResponse,
    InstallmentPlanListResponse,
)
from app.services.installment import (
    cancel_installment_plan,
    create_installment_plan,
    customer_ledger,
    customer_statement,
    list_installment_plans,
    read_installment_plan,
    receive_installment_payment,
    reverse_installment_payment,
)


router = APIRouter(
    prefix="/installments",
    tags=["Installments"],
)


CanViewInstallments = Annotated[
    User,
    Depends(
        require_permission(
            "installments.view"
        )
    ),
]


CanManageInstallments = Annotated[
    User,
    Depends(
        require_permission(
            "installments.manage"
        )
    ),
]


CanReceiveInstallmentPayments = (
    Annotated[
        User,
        Depends(
            require_permission(
                "payments.receive"
            )
        ),
    ]
)


CanReverseInstallmentPayments = (
    Annotated[
        User,
        Depends(
            require_permission(
                "payments.reverse"
            )
        ),
    ]
)


@router.get(
    "/customers/{customer_id}/ledger",
    response_model=CustomerLedgerResponse,
)
async def read_customer_ledger(
    customer_id: int,
    session: DatabaseSession,
    _: CanViewInstallments,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CustomerLedgerResponse:
    return await customer_ledger(
        session=session,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/customers/{customer_id}/statement",
    response_model=(
        CustomerStatementResponse
    ),
)
async def read_customer_statement(
    customer_id: int,
    session: DatabaseSession,
    _: CanViewInstallments,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CustomerStatementResponse:
    return await customer_statement(
        session=session,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "",
    response_model=(
        InstallmentPlanListResponse
    ),
)
async def read_installment_plans(
    session: DatabaseSession,
    _: CanViewInstallments,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    customer_id: int | None = Query(
        default=None,
        ge=1,
    ),
    invoice_id: int | None = Query(
        default=None,
        ge=1,
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
) -> InstallmentPlanListResponse:
    return await list_installment_plans(
        session=session,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        invoice_id=invoice_id,
        status_filter=status_filter,
    )


@router.post(
    "",
    response_model=(
        InstallmentPlanDetailResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_installment_plan_record(
    payload: InstallmentPlanCreate,
    session: DatabaseSession,
    current_user: CanManageInstallments,
) -> InstallmentPlanDetailResponse:
    return await create_installment_plan(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/{plan_id}",
    response_model=(
        InstallmentPlanDetailResponse
    ),
)
async def read_installment_plan_record(
    plan_id: int,
    session: DatabaseSession,
    _: CanViewInstallments,
) -> InstallmentPlanDetailResponse:
    return await read_installment_plan(
        session=session,
        plan_id=plan_id,
    )


@router.post(
    "/{plan_id}/payments",
    response_model=(
        InstallmentPaymentResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def receive_installment_payment_record(
    plan_id: int,
    payload: InstallmentPaymentCreate,
    session: DatabaseSession,
    current_user: (
        CanReceiveInstallmentPayments
    ),
) -> InstallmentPaymentResponse:
    return await receive_installment_payment(
        session=session,
        plan_id=plan_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{plan_id}/payments/{payment_id}/reverse",
    response_model=(
        InstallmentPaymentResponse
    ),
)
async def reverse_installment_payment_record(
    plan_id: int,
    payment_id: int,
    payload: InstallmentPaymentReverse,
    session: DatabaseSession,
    current_user: (
        CanReverseInstallmentPayments
    ),
) -> InstallmentPaymentResponse:
    return await reverse_installment_payment(
        session=session,
        plan_id=plan_id,
        payment_id=payment_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{plan_id}/cancel",
    response_model=(
        InstallmentPlanDetailResponse
    ),
)
async def cancel_installment_plan_record(
    plan_id: int,
    payload: InstallmentPlanCancel,
    session: DatabaseSession,
    current_user: CanManageInstallments,
) -> InstallmentPlanDetailResponse:
    return await cancel_installment_plan(
        session=session,
        plan_id=plan_id,
        payload=payload,
        current_user=current_user,
    )
