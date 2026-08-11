from io import BytesIO
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)
from fastapi.responses import StreamingResponse

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.services.documents import (
    build_payment_receipt_pdf,
    build_sales_invoice_pdf,
)
from app.services.payment_service import (
    get_payment_or_404,
)
from app.services.sales_service import (
    get_invoice,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


CanViewSales = Annotated[
    User,
    Depends(
        require_permission(
            "sales.view"
        )
    ),
]


CanViewPayments = Annotated[
    User,
    Depends(
        require_permission(
            "payments.view"
        )
    ),
]


@router.get(
    "/sales-invoices/{invoice_id}/pdf",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            },
            "description": (
                "Sales invoice PDF document"
            ),
        }
    },
)
async def download_sales_invoice_pdf(
    invoice_id: int,
    session: DatabaseSession,
    _: CanViewSales,
) -> StreamingResponse:
    invoice = await get_invoice(
        session,
        invoice_id,
    )

    pdf_bytes = await build_sales_invoice_pdf(
        session,
        invoice,
    )

    filename = (
        f"{invoice.invoice_number}.pdf"
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


@router.get(
    "/payment-receipts/{payment_id}/pdf",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            },
            "description": (
                "Payment receipt PDF document"
            ),
        }
    },
)
async def download_payment_receipt_pdf(
    payment_id: int,
    session: DatabaseSession,
    _: CanViewPayments,
) -> StreamingResponse:
    payment = await get_payment_or_404(
        session,
        payment_id,
    )

    pdf_bytes = await build_payment_receipt_pdf(
        session,
        payment,
    )

    filename = (
        f"{payment.receipt_number}.pdf"
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )
