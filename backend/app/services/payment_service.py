from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    CustomerPayment,
    InstallmentPlan,
    InstallmentPlanStatus,
    InvoiceStatus,
    PaymentStatus,
    SalesInvoice,
    User,
)
from app.services.audit import create_audit_log
from app.schemas.payment import (
    PaymentDetailResponse,
    PaymentListResponse,
    PaymentReceiveRequest,
    PaymentReverseRequest,
    PaymentTransactionResponse,
)


ZERO = Decimal("0.00")


async def _guard_active_installment_invoice(
    session: AsyncSession,
    invoice_id: int,
) -> None:
    result = await session.execute(
        select(InstallmentPlan.id)
        .where(
            InstallmentPlan.invoice_id
            == invoice_id,
            InstallmentPlan.status
            == (
                InstallmentPlanStatus
                .ACTIVE
                .value
            ),
        )
        .limit(1)
    )

    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "This invoice has an active "
                "installment plan. Use the "
                "installment payment endpoint."
            ),
        )


def money(
    value: Decimal,
) -> Decimal:
    return Decimal(value).quantize(
        Decimal("0.01")
    )



def payment_audit_snapshot(
    payment: CustomerPayment,
) -> dict:
    return {
        "payment_id": payment.id,
        "receipt_number":
            payment.receipt_number,
        "customer_id":
            payment.customer_id,
        "invoice_id":
            payment.invoice_id,
        "amount":
            str(money(payment.amount)),
        "payment_method":
            payment.payment_method,
        "reference_number":
            payment.reference_number,
        "is_reversed":
            payment.is_reversed,
        "reversed_at":
            payment.reversed_at,
        "reversal_reason":
            payment.reversal_reason,
    }


def invoice_payment_audit_snapshot(
    invoice: SalesInvoice,
) -> dict:
    return {
        "invoice_id":
            invoice.id,
        "invoice_number":
            invoice.invoice_number,
        "grand_total":
            str(money(invoice.grand_total)),
        "credited_amount":
            str(money(invoice.credited_amount)),
        "paid_amount":
            str(money(invoice.paid_amount)),
        "balance_amount":
            str(money(invoice.balance_amount)),
        "payment_status":
            invoice.payment_status,
        "invoice_status":
            invoice.invoice_status,
    }


def customer_payment_audit_snapshot(
    customer: Customer,
) -> dict:
    return {
        "customer_id":
            customer.id,
        "customer_number":
            customer.customer_number,
        "full_name":
            customer.full_name,
        "current_balance":
            str(
                money(
                    customer.current_balance
                )
            ),
    }


async def get_payment_or_404(
    session: AsyncSession,
    payment_id: int,
) -> CustomerPayment:
    payment = await session.get(
        CustomerPayment,
        payment_id,
    )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record was not found",
        )

    return payment


async def get_invoice_or_404(
    session: AsyncSession,
    invoice_id: int,
) -> SalesInvoice:
    invoice = await session.get(
        SalesInvoice,
        invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    return invoice


async def get_customer_or_404(
    session: AsyncSession,
    customer_id: int,
) -> Customer:
    customer = await session.get(
        Customer,
        customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer was not found",
        )

    return customer


async def build_payment_detail(
    session: AsyncSession,
    payment: CustomerPayment,
) -> PaymentDetailResponse:
    customer = await get_customer_or_404(
        session,
        payment.customer_id,
    )

    invoice = None

    if payment.invoice_id is not None:
        invoice = await session.get(
            SalesInvoice,
            payment.invoice_id,
        )

    return PaymentDetailResponse(
        id=payment.id,
        company_id=payment.company_id,
        branch_id=payment.branch_id,
        receipt_number=payment.receipt_number,
        customer_id=payment.customer_id,
        invoice_id=payment.invoice_id,
        payment_date=payment.payment_date,
        amount=payment.amount,
        payment_method=payment.payment_method,
        reference_number=(
            payment.reference_number
        ),
        notes=payment.notes,
        is_reversed=payment.is_reversed,
        reversed_at=payment.reversed_at,
        reversal_reason=(
            payment.reversal_reason
        ),
        created_by_id=payment.created_by_id,
        created_at=payment.created_at,
        invoice_number=(
            invoice.invoice_number
            if invoice is not None
            else None
        ),
        customer_number=(
            customer.customer_number
        ),
        customer_name=customer.full_name,
        customer_phone=(
            customer.primary_phone
        ),
        invoice_grand_total=(
            invoice.grand_total
            if invoice is not None
            else None
        ),
        invoice_paid_amount=(
            invoice.paid_amount
            if invoice is not None
            else None
        ),
        invoice_balance_amount=(
            invoice.balance_amount
            if invoice is not None
            else None
        ),
        invoice_payment_status=(
            invoice.payment_status
            if invoice is not None
            else None
        ),
    )


async def receive_invoice_payment(
    session: AsyncSession,
    payload: PaymentReceiveRequest,
    current_user: User,
) -> PaymentTransactionResponse:
    invoice = await get_invoice_or_404(
        session,
        payload.invoice_id,
    )

    await _guard_active_installment_invoice(
        session,
        invoice.id,
    )

    if invoice.invoice_status != (
        InvoiceStatus.CONFIRMED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Payments can only be received "
                "for confirmed invoices"
            ),
        )

    current_balance = money(
        invoice.balance_amount
    )

    if current_balance <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This invoice is already fully paid"
            ),
        )

    if payload.amount > current_balance:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Payment amount cannot exceed "
                f"invoice balance {current_balance}"
            ),
        )

    customer = await get_customer_or_404(
        session,
        invoice.customer_id,
    )

    invoice_before_snapshot = (
        invoice_payment_audit_snapshot(
            invoice
        )
    )

    customer_before_snapshot = (
        customer_payment_audit_snapshot(
            customer
        )
    )

    payment = CustomerPayment(
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        receipt_number=None,
        customer_id=invoice.customer_id,
        invoice_id=invoice.id,
        amount=money(payload.amount),
        payment_method=(
            payload.payment_method.value
        ),
        reference_number=(
            payload.reference_number
        ),
        notes=payload.notes,
        is_reversed=False,
        created_by_id=current_user.id,
    )

    session.add(payment)

    try:
        await session.flush()

        payment.receipt_number = (
            f"REC-{payment.id:06d}"
        )

        invoice.paid_amount = money(
            Decimal(invoice.paid_amount)
            + payload.amount
        )

        invoice.balance_amount = money(
            max(
                ZERO,
                Decimal(invoice.grand_total)
                - Decimal(
                    invoice.credited_amount
                )
                - Decimal(
                    invoice.paid_amount
                ),
            )
        )

        if invoice.balance_amount == ZERO:
            invoice.payment_status = (
                PaymentStatus.PAID.value
            )
        else:
            invoice.payment_status = (
                PaymentStatus.PARTIAL.value
            )

        invoice.updated_by_id = (
            current_user.id
        )

        customer.current_balance = money(
            max(
                ZERO,
                Decimal(
                    customer.current_balance
                )
                - payload.amount,
            )
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="payment.received",
            module="payments",
            entity_type="customer_payment",
            entity_id=payment.id,
            entity_reference=(
                payment.receipt_number
            ),
            description=(
                f"Payment "
                f"{payment.receipt_number} "
                "received"
            ),
            before_data={
                "invoice":
                    invoice_before_snapshot,
                "customer":
                    customer_before_snapshot,
            },
            after_data={
                "payment":
                    payment_audit_snapshot(
                        payment
                    ),
                "invoice":
                    invoice_payment_audit_snapshot(
                        invoice
                    ),
                "customer":
                    customer_payment_audit_snapshot(
                        customer
                    ),
            },
            metadata={
                "invoice_id":
                    invoice.id,
                "customer_id":
                    customer.id,
                "payment_method":
                    payment.payment_method,
            },
        )

        await session.commit()

        await session.refresh(payment)
        await session.refresh(invoice)
        await session.refresh(customer)

    except Exception:
        await session.rollback()
        raise

    detail = await build_payment_detail(
        session,
        payment,
    )

    return PaymentTransactionResponse(
        message=(
            "Customer payment recorded "
            "successfully"
        ),
        payment=detail,
        invoice_id=invoice.id,
        invoice_number=(
            invoice.invoice_number
        ),
        grand_total=invoice.grand_total,
        paid_amount=invoice.paid_amount,
        balance_amount=invoice.balance_amount,
        payment_status=(
            invoice.payment_status
        ),
        customer_id=customer.id,
        customer_balance=(
            customer.current_balance
        ),
    )


async def reverse_invoice_payment(
    session: AsyncSession,
    payment_id: int,
    payload: PaymentReverseRequest,
    current_user: User,
) -> PaymentTransactionResponse:
    payment = await get_payment_or_404(
        session,
        payment_id,
    )

    if payment.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This payment has already "
                "been reversed"
            ),
        )

    if payment.invoice_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only invoice-linked payments "
                "can be reversed here"
            ),
        )

    invoice = await get_invoice_or_404(
        session,
        payment.invoice_id,
    )

    await _guard_active_installment_invoice(
        session,
        invoice.id,
    )

    customer = await get_customer_or_404(
        session,
        payment.customer_id,
    )

    payment_before_snapshot = (
        payment_audit_snapshot(
            payment
        )
    )

    invoice_before_snapshot = (
        invoice_payment_audit_snapshot(
            invoice
        )
    )

    customer_before_snapshot = (
        customer_payment_audit_snapshot(
            customer
        )
    )

    payment_amount = money(
        payment.amount
    )

    if payment_amount > money(
        invoice.paid_amount
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Payment reversal would make "
                "invoice paid amount negative"
            ),
        )

    try:
        payment.is_reversed = True
        payment.reversed_at = (
            datetime.now(timezone.utc)
        )
        payment.reversal_reason = (
            payload.reason
        )

        invoice.paid_amount = money(
            Decimal(invoice.paid_amount)
            - payment_amount
        )

        invoice.balance_amount = money(
            max(
                ZERO,
                Decimal(invoice.grand_total)
                - Decimal(
                    invoice.credited_amount
                )
                - Decimal(invoice.paid_amount),
            )
        )

        if invoice.paid_amount == ZERO:
            invoice.payment_status = (
                PaymentStatus.UNPAID.value
            )
        elif invoice.balance_amount == ZERO:
            invoice.payment_status = (
                PaymentStatus.PAID.value
            )
        else:
            invoice.payment_status = (
                PaymentStatus.PARTIAL.value
            )

        invoice.updated_by_id = (
            current_user.id
        )

        customer.current_balance = money(
            Decimal(
                customer.current_balance
            )
            + payment_amount
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="payment.reversed",
            module="payments",
            entity_type="customer_payment",
            entity_id=payment.id,
            entity_reference=(
                payment.receipt_number
            ),
            description=(
                f"Payment "
                f"{payment.receipt_number} "
                "reversed"
            ),
            before_data={
                "payment":
                    payment_before_snapshot,
                "invoice":
                    invoice_before_snapshot,
                "customer":
                    customer_before_snapshot,
            },
            after_data={
                "payment":
                    payment_audit_snapshot(
                        payment
                    ),
                "invoice":
                    invoice_payment_audit_snapshot(
                        invoice
                    ),
                "customer":
                    customer_payment_audit_snapshot(
                        customer
                    ),
            },
            metadata={
                "invoice_id":
                    invoice.id,
                "customer_id":
                    customer.id,
                "reversal_reason":
                    payload.reason,
            },
        )

        await session.commit()

        await session.refresh(payment)
        await session.refresh(invoice)
        await session.refresh(customer)

    except Exception:
        await session.rollback()
        raise

    detail = await build_payment_detail(
        session,
        payment,
    )

    return PaymentTransactionResponse(
        message=(
            "Payment reversed successfully"
        ),
        payment=detail,
        invoice_id=invoice.id,
        invoice_number=(
            invoice.invoice_number
        ),
        grand_total=invoice.grand_total,
        paid_amount=invoice.paid_amount,
        balance_amount=invoice.balance_amount,
        payment_status=(
            invoice.payment_status
        ),
        customer_id=customer.id,
        customer_balance=(
            customer.current_balance
        ),
    )


async def list_payments(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    customer_id: int | None,
    invoice_id: int | None,
    is_reversed: bool | None,
) -> PaymentListResponse:
    filters = []

    if customer_id is not None:
        filters.append(
            CustomerPayment.customer_id
            == customer_id
        )

    if invoice_id is not None:
        filters.append(
            CustomerPayment.invoice_id
            == invoice_id
        )

    if is_reversed is not None:
        filters.append(
            CustomerPayment.is_reversed.is_(
                is_reversed
            )
        )

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                CustomerPayment
                .receipt_number.ilike(pattern),
                CustomerPayment
                .reference_number.ilike(pattern),
                Customer.full_name.ilike(
                    pattern
                ),
                Customer.primary_phone.ilike(
                    pattern
                ),
                SalesInvoice
                .invoice_number.ilike(pattern),
            )
        )

    count_statement = (
        select(func.count())
        .select_from(CustomerPayment)
        .join(
            Customer,
            Customer.id
            == CustomerPayment.customer_id,
        )
        .outerjoin(
            SalesInvoice,
            SalesInvoice.id
            == CustomerPayment.invoice_id,
        )
        .where(*filters)
    )

    total = int(
        await session.scalar(
            count_statement
        )
        or 0
    )

    statement = (
        select(CustomerPayment)
        .join(
            Customer,
            Customer.id
            == CustomerPayment.customer_id,
        )
        .outerjoin(
            SalesInvoice,
            SalesInvoice.id
            == CustomerPayment.invoice_id,
        )
        .where(*filters)
        .order_by(
            CustomerPayment
            .payment_date.desc(),
            CustomerPayment.id.desc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    result = await session.execute(
        statement
    )

    payments = result.scalars().all()

    items = [
        await build_payment_detail(
            session,
            payment,
        )
        for payment in payments
    ]

    return PaymentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(
            ceil(total / page_size)
            if total
            else 0
        ),
    )
