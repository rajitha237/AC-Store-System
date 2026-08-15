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
from app.models.company import Company
from app.services.documents import (
    JobCardPDFData,
    build_job_card_pdf,
    build_payment_receipt_pdf,
    build_sales_invoice_pdf,
)
from app.services.payment_service import (
    get_payment_or_404,
)
from app.services.sales_service import (
    get_invoice,
)
from app.services.service import (
    get_job_card,
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



CanViewJobs = Annotated[
    User,
    Depends(
        require_permission(
            "job_cards.view"
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


@router.get(
    "/service-jobs/{job_id}/pdf",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            },
            "description": (
                "Service job card PDF document"
            ),
        }
    },
)
async def download_service_job_card_pdf(
    job_id: int,
    session: DatabaseSession,
    current_user: CanViewJobs,
) -> StreamingResponse:
    # Read-only fetch through the existing service
    # layer so relationships are loaded consistently.
    job = await get_job_card(
        session,
        job_id,
    )

    company = await session.get(
        Company,
        job.company_id,
    )

    customer = job.customer

    address_parts = []

    if customer is not None:
        for value in (
            customer.address_line_1,
            customer.address_line_2,
            customer.city,
        ):
            if value and value.strip():
                address_parts.append(
                    value.strip()
                )

    customer_address = (
        ", ".join(address_parts)
        if address_parts
        else "-"
    )

    customer_name = (
        customer.full_name
        if customer is not None
        else "-"
    )

    customer_mobile = (
        customer.primary_phone
        if customer is not None
        else "-"
    )

    receiving_officer = (
        job.receiving_officer.full_name
        if job.receiving_officer is not None
        else None
    )

    product_name = (
        getattr(
            job.product,
            "name",
            None,
        )
        if job.product is not None
        else None
    )

    company_name = (
        company.name
        if company is not None
        else "BANDARA COOL WORLD"
    )

    company_address = (
        company.address
        if (
            company is not None
            and company.address
        )
        else ""
    )

    company_phone = (
        company.phone
        if (
            company is not None
            and company.phone
        )
        else ""
    )

    logo_path = (
        company.logo_path
        if company is not None
        else None
    )

    pdf_bytes = build_job_card_pdf(
        JobCardPDFData(
            company_name=company_name,
            company_address=company_address,
            company_phone=company_phone,
            logo_path=logo_path,

            job_number=(
                job.job_number
                or str(job.id)
            ),

            customer_name=customer_name,
            customer_address=customer_address,
            mobile=customer_mobile,

            create_datetime=job.received_at,

            user_name=(
                current_user.full_name
                or current_user.username
            ),

            handover_date=(
                job.expected_completion_date
            ),

            job_type=job.service_type,

            receiving_officer=(
                receiving_officer
            ),

            brand=job.brand_name,

            model=(
                job.model_number
                or product_name
            ),

            color=job.item_color,

            common=(
                job.accessories_received
                or job.reported_issue
            ),

            problems=job.complaint,

            imei_number=(
                job.secondary_serial_number
            ),

            serial_number=job.serial_number,

            battery_condition=(
                job.physical_condition
            ),

            special_note=(
                job.special_notes
                or job.technician_diagnosis
            ),

            estimate_cost=job.estimated_cost,

            terms_and_conditions=None,
        )
    )

    filename = (
        f"{job.job_number or job.id}.pdf"
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

