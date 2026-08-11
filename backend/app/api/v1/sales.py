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
from app.models import (
    InvoiceStatus,
    PaymentStatus,
    User,
)
from app.schemas.sales import (
    CustomerPaymentResponse,
    PaymentCreate,
    SalesInvoiceConfirmRequest,
    SalesInvoiceCreate,
    SalesInvoiceDetailResponse,
    SalesInvoiceListResponse,
    SalesInvoiceResponse,
)
from app.services.sales_service import (
    confirm_invoice,
    create_draft_invoice,
    get_invoice,
    invoice_detail_response,
    list_invoices,
    post_payment,
)

router = APIRouter(
    prefix="/sales",
    tags=["Sales"],
)

CanViewSales = Annotated[
    User,
    Depends(
        require_permission("sales.view")
    ),
]

CanCreateSales = Annotated[
    User,
    Depends(
        require_permission("sales.create")
    ),
]

CanReceivePayments = Annotated[
    User,
    Depends(
        require_permission("payments.receive")
    ),
]


@router.post(
    "/invoices",
    response_model=SalesInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice(
    payload: SalesInvoiceCreate,
    session: DatabaseSession,
    current_user: CanCreateSales,
) -> SalesInvoiceResponse:
    invoice = await create_draft_invoice(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return SalesInvoiceResponse.model_validate(
        invoice
    )


@router.get(
    "/invoices",
    response_model=SalesInvoiceListResponse,
)
async def read_invoices(
    session: DatabaseSession,
    _: CanViewSales,
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
    invoice_status: InvoiceStatus | None = None,
    payment_status: PaymentStatus | None = None,
) -> SalesInvoiceListResponse:
    return await list_invoices(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        invoice_status=(
            invoice_status.value
            if invoice_status is not None
            else None
        ),
        payment_status=(
            payment_status.value
            if payment_status is not None
            else None
        ),
    )


@router.get(
    "/invoices/{invoice_id}",
    response_model=SalesInvoiceDetailResponse,
)
async def read_invoice(
    invoice_id: int,
    session: DatabaseSession,
    _: CanViewSales,
) -> SalesInvoiceDetailResponse:
    invoice = await get_invoice(
        session,
        invoice_id,
    )

    return await invoice_detail_response(
        session,
        invoice,
    )


@router.post(
    "/invoices/{invoice_id}/confirm",
    response_model=SalesInvoiceDetailResponse,
)
async def confirm_sales_invoice(
    invoice_id: int,
    payload: SalesInvoiceConfirmRequest,
    session: DatabaseSession,
    current_user: CanCreateSales,
) -> SalesInvoiceDetailResponse:
    invoice = await confirm_invoice(
        session=session,
        invoice_id=invoice_id,
        payload=payload,
        current_user=current_user,
    )

    return await invoice_detail_response(
        session,
        invoice,
    )


@router.post(
    "/payments",
    response_model=CustomerPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    payload: PaymentCreate,
    session: DatabaseSession,
    current_user: CanReceivePayments,
) -> CustomerPaymentResponse:
    payment = await post_payment(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return CustomerPaymentResponse.model_validate(
        payment
    )
