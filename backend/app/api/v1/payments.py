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
from app.schemas.payment import (
    PaymentDetailResponse,
    PaymentListResponse,
    PaymentReceiveRequest,
    PaymentReverseRequest,
    PaymentTransactionResponse,
)
from app.services.payment_service import (
    build_payment_detail,
    get_payment_or_404,
    list_payments,
    receive_invoice_payment,
    reverse_invoice_payment,
)


router = APIRouter(
    prefix="/payments",
    tags=["Customer Payments"],
)


CanViewPayments = Annotated[
    User,
    Depends(
        require_permission(
            "payments.view"
        )
    ),
]


CanReceivePayments = Annotated[
    User,
    Depends(
        require_permission(
            "payments.receive"
        )
    ),
]


CanReversePayments = Annotated[
    User,
    Depends(
        require_permission(
            "payments.reverse"
        )
    ),
]


@router.get(
    "",
    response_model=PaymentListResponse,
)
async def read_payments(
    session: DatabaseSession,
    _: CanViewPayments,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    customer_id: int | None = Query(
        default=None,
        ge=1,
    ),
    invoice_id: int | None = Query(
        default=None,
        ge=1,
    ),
    is_reversed: bool | None = None,
) -> PaymentListResponse:
    return await list_payments(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        customer_id=customer_id,
        invoice_id=invoice_id,
        is_reversed=is_reversed,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
)
async def read_payment(
    payment_id: int,
    session: DatabaseSession,
    _: CanViewPayments,
) -> PaymentDetailResponse:
    payment = await get_payment_or_404(
        session,
        payment_id,
    )

    return await build_payment_detail(
        session,
        payment,
    )


@router.post(
    "",
    response_model=PaymentTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def receive_payment(
    payload: PaymentReceiveRequest,
    session: DatabaseSession,
    current_user: CanReceivePayments,
) -> PaymentTransactionResponse:
    return await receive_invoice_payment(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{payment_id}/reverse",
    response_model=PaymentTransactionResponse,
)
async def reverse_payment(
    payment_id: int,
    payload: PaymentReverseRequest,
    session: DatabaseSession,
    current_user: CanReversePayments,
) -> PaymentTransactionResponse:
    return await reverse_invoice_payment(
        session=session,
        payment_id=payment_id,
        payload=payload,
        current_user=current_user,
    )
