from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CreditNote,
    CreditNoteStatus,
    Customer,
    CustomerRefund,
    RefundStatus,
    SalesInvoice,
    User,
)
from app.models.returns import (
    ReturnResolution,
    ReturnStatus,
    SalesReturn,
)
from app.models.sales import (
    InvoiceStatus,
    PaymentStatus,
)
from app.services.audit import create_audit_log
from app.schemas.credit_note import (
    CreditNoteApprovalRequest,
    CreditNoteCreate,
    CreditNoteDetailResponse,
    CustomerRefundResponse,
    FinancialReversalRequest,
    RefundCreate,
)
from app.services.returns import (
    add_status_history,
    reverse_returned_stock,
    receive_returned_stock,
)


ZERO_2 = Decimal("0.00")


def money(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def invoice_audit_snapshot(
    invoice: SalesInvoice,
) -> dict[str, str | int | None]:
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "grand_total": str(
            money(invoice.grand_total)
        ),
        "credited_amount": str(
            money(invoice.credited_amount)
        ),
        "paid_amount": str(
            money(invoice.paid_amount)
        ),
        "balance_amount": str(
            money(invoice.balance_amount)
        ),
        "payment_status":
            invoice.payment_status,
        "invoice_status":
            invoice.invoice_status,
    }


def credit_note_audit_snapshot(
    credit_note: CreditNote,
) -> dict[str, str | int | bool | None]:
    return {
        "credit_note_id": credit_note.id,
        "credit_note_number":
            credit_note.credit_note_number,
        "invoice_id": credit_note.invoice_id,
        "return_id": credit_note.return_id,
        "customer_id": credit_note.customer_id,
        "amount": str(
            money(credit_note.amount)
        ),
        "status": credit_note.status,
        "is_reversed":
            credit_note.is_reversed,
    }


def refund_audit_snapshot(
    refund: CustomerRefund,
) -> dict[str, str | int | bool | None]:
    return {
        "refund_id": refund.id,
        "refund_number":
            refund.refund_number,
        "credit_note_id":
            refund.credit_note_id,
        "invoice_id": refund.invoice_id,
        "return_id": refund.return_id,
        "customer_id": refund.customer_id,
        "amount": str(
            money(refund.amount)
        ),
        "refund_method":
            refund.refund_method,
        "status": refund.status,
        "is_reversed":
            refund.is_reversed,
    }




def net_invoice_total(
    invoice: SalesInvoice,
) -> Decimal:
    return money(
        max(
            ZERO_2,
            Decimal(invoice.grand_total)
            - Decimal(invoice.credited_amount),
        )
    )


def invoice_outstanding(
    invoice: SalesInvoice,
) -> Decimal:
    return money(
        max(
            ZERO_2,
            net_invoice_total(invoice)
            - Decimal(invoice.paid_amount),
        )
    )


def invoice_overpayment(
    invoice: SalesInvoice,
) -> Decimal:
    return money(
        max(
            ZERO_2,
            Decimal(invoice.paid_amount)
            - net_invoice_total(invoice),
        )
    )


def synchronize_payment_status(
    invoice: SalesInvoice,
) -> None:
    net_total = net_invoice_total(invoice)

    paid = money(
        invoice.paid_amount
    )

    invoice.balance_amount = money(
        max(
            ZERO_2,
            net_total - paid,
        )
    )

    if (
        net_total == ZERO_2
        and paid == ZERO_2
        and Decimal(invoice.credited_amount)
        > ZERO_2
    ):
        invoice.payment_status = (
            PaymentStatus.REFUNDED.value
        )

    elif paid <= ZERO_2:
        invoice.payment_status = (
            PaymentStatus.UNPAID.value
        )

    elif paid < net_total:
        invoice.payment_status = (
            PaymentStatus.PARTIAL.value
        )

    else:
        invoice.payment_status = (
            PaymentStatus.PAID.value
        )

    if (
        Decimal(invoice.credited_amount)
        >= Decimal(invoice.grand_total)
    ):
        invoice.invoice_status = (
            InvoiceStatus.RETURNED.value
        )


async def get_credit_note(
    session: AsyncSession,
    credit_note_id: int,
) -> CreditNote:
    result = await session.execute(
        select(CreditNote)
        .options(
            selectinload(
                CreditNote.refunds
            )
        )
        .where(
            CreditNote.id
            == credit_note_id
        )
    )

    credit_note = (
        result.scalar_one_or_none()
    )

    if credit_note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit note was not found",
        )

    return credit_note


async def active_refund_total(
    session: AsyncSession,
    credit_note_id: int,
) -> Decimal:
    value = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    CustomerRefund.amount
                ),
                ZERO_2,
            )
        )
        .where(
            CustomerRefund.credit_note_id
            == credit_note_id,
            CustomerRefund.status
            == RefundStatus.POSTED.value,
            CustomerRefund.is_reversed.is_(
                False
            ),
        )
    )

    return money(
        value or ZERO_2
    )


async def build_credit_note_detail(
    session: AsyncSession,
    credit_note: CreditNote,
) -> CreditNoteDetailResponse:
    invoice = await session.get(
        SalesInvoice,
        credit_note.invoice_id,
    )

    sales_return_result = await session.execute(
        select(SalesReturn)
        .options(
            selectinload(SalesReturn.items),
            selectinload(
                SalesReturn.status_history
            ),
        )
        .where(
            SalesReturn.id
            == credit_note.return_id
        )
    )

    sales_return = (
        sales_return_result
        .scalars()
        .unique()
        .one_or_none()
    )

    customer = await session.get(
        Customer,
        credit_note.customer_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Credit note invoice "
                "was not found"
            ),
        )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Credit note return "
                "was not found"
            ),
        )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Credit note customer "
                "was not found"
            ),
        )

    refund_total = (
        await active_refund_total(
            session,
            credit_note.id,
        )
    )

    return CreditNoteDetailResponse(
        id=credit_note.id,
        company_id=credit_note.company_id,
        branch_id=credit_note.branch_id,
        credit_note_number=(
            credit_note.credit_note_number
        ),
        invoice_id=credit_note.invoice_id,
        return_id=credit_note.return_id,
        customer_id=credit_note.customer_id,
        amount=credit_note.amount,
        status=credit_note.status,
        reason=credit_note.reason,
        notes=credit_note.notes,
        approved_by_id=(
            credit_note.approved_by_id
        ),
        approved_at=(
            credit_note.approved_at
        ),
        posted_by_id=(
            credit_note.posted_by_id
        ),
        posted_at=credit_note.posted_at,
        is_reversed=(
            credit_note.is_reversed
        ),
        reversed_by_id=(
            credit_note.reversed_by_id
        ),
        reversed_at=(
            credit_note.reversed_at
        ),
        reversal_reason=(
            credit_note.reversal_reason
        ),
        created_by_id=(
            credit_note.created_by_id
        ),
        created_at=credit_note.created_at,
        updated_at=credit_note.updated_at,
        invoice_number=(
            invoice.invoice_number
        ),
        return_number=(
            sales_return.return_number
        ),
        customer_name=customer.full_name,
        customer_phone=(
            customer.primary_phone
        ),
        invoice_grand_total=(
            invoice.grand_total
        ),
        invoice_paid_amount=(
            invoice.paid_amount
        ),
        invoice_balance_amount=(
            invoice.balance_amount
        ),
        active_refund_total=refund_total,
        refundable_overpayment=(
            invoice_overpayment(invoice)
        ),
        refunds=[
            CustomerRefundResponse
            .model_validate(refund)
            for refund
            in credit_note.refunds
        ],
    )


async def create_credit_note(
    session: AsyncSession,
    payload: CreditNoteCreate,
    current_user: User,
) -> CreditNote:
    sales_return = await session.get(
        SalesReturn,
        payload.return_id,
    )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    if sales_return.status != (
        ReturnStatus.APPROVED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Return must be approved before "
                "creating a credit note"
            ),
        )

    if sales_return.resolution != (
        ReturnResolution.REFUND.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Credit notes can only be created "
                "for refund returns"
            ),
        )

    amount = money(
        sales_return.refund_amount
    )

    if amount <= ZERO_2:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Approved refund amount "
                "must be greater than zero"
            ),
        )

    existing = await session.scalar(
        select(CreditNote)
        .where(
            CreditNote.return_id
            == sales_return.id
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A credit note already exists "
                "for this return"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        sales_return.invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    remaining_creditable = money(
        Decimal(invoice.grand_total)
        - Decimal(invoice.credited_amount)
    )

    if amount > remaining_creditable:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Credit note amount exceeds "
                "remaining invoice value"
            ),
        )

    credit_note = CreditNote(
        company_id=sales_return.company_id,
        branch_id=sales_return.branch_id,
        credit_note_number=None,
        invoice_id=invoice.id,
        return_id=sales_return.id,
        customer_id=(
            sales_return.customer_id
        ),
        amount=amount,
        status=(
            CreditNoteStatus.DRAFT.value
        ),
        reason=sales_return.reason,
        notes=payload.notes,
        approved_by_id=None,
        approved_at=None,
        posted_by_id=None,
        posted_at=None,
        is_reversed=False,
        reversed_by_id=None,
        reversed_at=None,
        reversal_reason=None,
        created_by_id=current_user.id,
    )

    session.add(credit_note)

    try:
        await session.flush()

        credit_note.credit_note_number = (
            f"CN-{credit_note.id:06d}"
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="credit_note.created",
            module="credit_notes",
            entity_type="credit_note",
            entity_id=credit_note.id,
            entity_reference=(
                credit_note.credit_note_number
            ),
            description=(
                f"Credit note "
                f"{credit_note.credit_note_number} "
                "created"
            ),
            before_data=None,
            after_data=(
                credit_note_audit_snapshot(
                    credit_note
                )
            ),
            metadata={
                "invoice_id":
                    credit_note.invoice_id,
                "return_id":
                    credit_note.return_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_credit_note(
        session,
        credit_note.id,
    )


async def approve_credit_note(
    session: AsyncSession,
    credit_note_id: int,
    payload: CreditNoteApprovalRequest,
    current_user: User,
) -> CreditNote:
    credit_note = await get_credit_note(
        session,
        credit_note_id,
    )

    if credit_note.status != (
        CreditNoteStatus.DRAFT.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only draft credit notes "
                "can be approved"
            ),
        )

    before_snapshot = (
        credit_note_audit_snapshot(
            credit_note
        )
    )

    credit_note.status = (
        CreditNoteStatus.APPROVED.value
    )

    credit_note.approved_by_id = (
        current_user.id
    )

    credit_note.approved_at = utc_now()

    if payload.notes is not None:
        credit_note.notes = payload.notes

    try:
        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="credit_note.approved",
            module="credit_notes",
            entity_type="credit_note",
            entity_id=credit_note.id,
            entity_reference=(
                credit_note.credit_note_number
            ),
            description=(
                f"Credit note "
                f"{credit_note.credit_note_number} "
                "approved"
            ),
            before_data=before_snapshot,
            after_data=(
                credit_note_audit_snapshot(
                    credit_note
                )
            ),
            metadata={
                "invoice_id":
                    credit_note.invoice_id,
                "return_id":
                    credit_note.return_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_credit_note(
        session,
        credit_note_id,
    )


async def post_credit_note(
    session: AsyncSession,
    credit_note_id: int,
    current_user: User,
) -> CreditNote:
    credit_note = await get_credit_note(
        session,
        credit_note_id,
    )

    if credit_note.status != (
        CreditNoteStatus.APPROVED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only approved credit notes "
                "can be posted"
            ),
        )

    if credit_note.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reversed credit note "
                "cannot be posted"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        credit_note.invoice_id,
    )

    sales_return_result = await session.execute(
        select(SalesReturn)
        .options(
            selectinload(SalesReturn.items),
            selectinload(
                SalesReturn.status_history
            ),
        )
        .where(
            SalesReturn.id
            == credit_note.return_id
        )
    )

    sales_return = (
        sales_return_result
        .scalars()
        .unique()
        .one_or_none()
    )

    customer = await session.get(
        Customer,
        credit_note.customer_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer was not found",
        )

    invoice_before_snapshot = (
        invoice_audit_snapshot(
            invoice
        )
    )

    credit_note_before_snapshot = (
        credit_note_audit_snapshot(
            credit_note
        )
    )

    old_balance = money(
        invoice.balance_amount
    )

    new_credited_amount = money(
        Decimal(invoice.credited_amount)
        + Decimal(credit_note.amount)
    )

    if (
        new_credited_amount
        > Decimal(invoice.grand_total)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Posting this credit note would "
                "over-credit the invoice"
            ),
        )

    try:
        await receive_returned_stock(
            session,
            sales_return,
            current_user,
        )

        invoice.credited_amount = (
            new_credited_amount
        )

        synchronize_payment_status(
            invoice
        )

        new_balance = money(
            invoice.balance_amount
        )

        receivable_reduction = money(
            old_balance - new_balance
        )

        if receivable_reduction > ZERO_2:
            current_customer_balance = money(
                customer.current_balance
            )

            if (
                current_customer_balance
                < receivable_reduction
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Customer balance is "
                        "inconsistent with invoice "
                        "receivable balance"
                    ),
                )

            customer.current_balance = money(
                current_customer_balance
                - receivable_reduction
            )

        credit_note.status = (
            CreditNoteStatus.POSTED.value
        )

        credit_note.posted_by_id = (
            current_user.id
        )

        credit_note.posted_at = utc_now()

        old_return_status = (
            sales_return.status
        )

        sales_return.status = (
            ReturnStatus.PROCESSING.value
        )

        sales_return.updated_by_id = (
            current_user.id
        )

        await add_status_history(
            session,
            sales_return=sales_return,
            old_status=old_return_status,
            new_status=(
                ReturnStatus.PROCESSING.value
            ),
            current_user=current_user,
            remarks=(
                f"Credit note "
                f"{credit_note.credit_note_number} "
                "posted"
            ),
        )

        if (
            invoice_overpayment(invoice)
            == ZERO_2
        ):
            sales_return.status = (
                ReturnStatus.COMPLETED.value
            )

            sales_return.completed_at = (
                utc_now()
            )

            await add_status_history(
                session,
                sales_return=sales_return,
                old_status=(
                    ReturnStatus.PROCESSING.value
                ),
                new_status=(
                    ReturnStatus.COMPLETED.value
                ),
                current_user=current_user,
                remarks=(
                    "Return completed with "
                    "credit note adjustment"
                ),
            )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="credit_note.posted",
            module="credit_notes",
            entity_type="credit_note",
            entity_id=credit_note.id,
            entity_reference=(
                credit_note.credit_note_number
            ),
            description=(
                f"Credit note "
                f"{credit_note.credit_note_number} "
                "posted"
            ),
            before_data={
                "credit_note":
                    credit_note_before_snapshot,
                "invoice":
                    invoice_before_snapshot,
            },
            after_data={
                "credit_note":
                    credit_note_audit_snapshot(
                        credit_note
                    ),
                "invoice":
                    invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "return_id":
                    credit_note.return_id,
                "customer_id":
                    credit_note.customer_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_credit_note(
        session,
        credit_note_id,
    )


async def create_refund(
    session: AsyncSession,
    payload: RefundCreate,
    current_user: User,
) -> CustomerRefund:
    credit_note = await get_credit_note(
        session,
        payload.credit_note_id,
    )

    if credit_note.status != (
        CreditNoteStatus.POSTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Refund can only be created "
                "for a posted credit note"
            ),
        )

    if credit_note.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot refund a reversed "
                "credit note"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        credit_note.invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    amount = money(
        payload.amount
    )

    overpayment = (
        invoice_overpayment(invoice)
    )

    if amount > overpayment:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Refund amount exceeds current "
                f"refundable overpayment "
                f"{overpayment}"
            ),
        )

    already_refunded = (
        await active_refund_total(
            session,
            credit_note.id,
        )
    )

    remaining_credit_note_amount = money(
        Decimal(credit_note.amount)
        - already_refunded
    )

    if amount > remaining_credit_note_amount:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Refund amount exceeds remaining "
                "credit note refund value"
            ),
        )

    refund = CustomerRefund(
        company_id=credit_note.company_id,
        branch_id=credit_note.branch_id,
        refund_number=None,
        credit_note_id=credit_note.id,
        return_id=credit_note.return_id,
        invoice_id=credit_note.invoice_id,
        customer_id=credit_note.customer_id,
        amount=amount,
        refund_method=(
            payload.refund_method.value
        ),
        status=RefundStatus.PENDING.value,
        reference_number=(
            payload.reference_number
        ),
        notes=payload.notes,
        posted_by_id=None,
        posted_at=None,
        is_reversed=False,
        reversed_by_id=None,
        reversed_at=None,
        reversal_reason=None,
        created_by_id=current_user.id,
    )

    session.add(refund)

    try:
        await session.flush()

        refund.refund_number = (
            f"RF-{refund.id:06d}"
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="refund.created",
            module="refunds",
            entity_type="customer_refund",
            entity_id=refund.id,
            entity_reference=(
                refund.refund_number
            ),
            description=(
                f"Customer refund "
                f"{refund.refund_number} "
                "created"
            ),
            before_data=None,
            after_data=(
                refund_audit_snapshot(
                    refund
                )
            ),
            metadata={
                "credit_note_id":
                    refund.credit_note_id,
                "invoice_id":
                    refund.invoice_id,
                "return_id":
                    refund.return_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return refund


async def post_refund(
    session: AsyncSession,
    refund_id: int,
    current_user: User,
) -> CustomerRefund:
    refund = await session.get(
        CustomerRefund,
        refund_id,
    )

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer refund was not found",
        )

    if refund.status != (
        RefundStatus.PENDING.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only pending refunds "
                "can be posted"
            ),
        )

    if refund.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reversed refund cannot be posted"
            ),
        )

    credit_note = await get_credit_note(
        session,
        refund.credit_note_id,
    )

    if credit_note.status != (
        CreditNoteStatus.POSTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Credit note must remain posted "
                "before refund processing"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        refund.invoice_id,
    )

    sales_return = await session.get(
        SalesReturn,
        refund.return_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    invoice_before_snapshot = (
        invoice_audit_snapshot(
            invoice
        )
    )

    refund_before_snapshot = (
        refund_audit_snapshot(
            refund
        )
    )

    amount = money(
        refund.amount
    )

    available_overpayment = (
        invoice_overpayment(invoice)
    )

    if amount > available_overpayment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Refund amount exceeds current "
                "invoice overpayment"
            ),
        )

    try:
        invoice.paid_amount = money(
            Decimal(invoice.paid_amount)
            - amount
        )

        if invoice.paid_amount < ZERO_2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Refund would create a "
                    "negative invoice paid amount"
                ),
            )

        synchronize_payment_status(
            invoice
        )

        refund.status = (
            RefundStatus.POSTED.value
        )

        refund.posted_by_id = (
            current_user.id
        )

        refund.posted_at = utc_now()

        if (
            invoice_overpayment(invoice)
            == ZERO_2
        ):
            old_status = (
                sales_return.status
            )

            sales_return.status = (
                ReturnStatus.COMPLETED.value
            )

            sales_return.completed_at = (
                utc_now()
            )

            sales_return.updated_by_id = (
                current_user.id
            )

            if old_status != (
                ReturnStatus.COMPLETED.value
            ):
                await add_status_history(
                    session,
                    sales_return=sales_return,
                    old_status=old_status,
                    new_status=(
                        ReturnStatus
                        .COMPLETED.value
                    ),
                    current_user=current_user,
                    remarks=(
                        f"Refund "
                        f"{refund.refund_number} "
                        "posted"
                    ),
                )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="refund.posted",
            module="refunds",
            entity_type="customer_refund",
            entity_id=refund.id,
            entity_reference=(
                refund.refund_number
            ),
            description=(
                f"Customer refund "
                f"{refund.refund_number} "
                "posted"
            ),
            before_data={
                "refund":
                    refund_before_snapshot,
                "invoice":
                    invoice_before_snapshot,
            },
            after_data={
                "refund":
                    refund_audit_snapshot(
                        refund
                    ),
                "invoice":
                    invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "credit_note_id":
                    refund.credit_note_id,
                "return_id":
                    refund.return_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return refund


async def reverse_refund(
    session: AsyncSession,
    refund_id: int,
    payload: FinancialReversalRequest,
    current_user: User,
) -> CustomerRefund:
    refund = await session.get(
        CustomerRefund,
        refund_id,
    )

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer refund was not found",
        )

    if refund.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This refund has already "
                "been reversed"
            ),
        )

    if refund.status != (
        RefundStatus.POSTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only posted refunds "
                "can be reversed"
            ),
        )

    credit_note = await get_credit_note(
        session,
        refund.credit_note_id,
    )

    if credit_note.status != (
        CreditNoteStatus.POSTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Refund cannot be reversed because "
                "its credit note is not posted"
            ),
        )

    if credit_note.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Refund cannot be reversed after "
                "its credit note was reversed"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        refund.invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    sales_return = await session.get(
        SalesReturn,
        refund.return_id,
    )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    invoice_before_snapshot = (
        invoice_audit_snapshot(
            invoice
        )
    )

    refund_before_snapshot = (
        refund_audit_snapshot(
            refund
        )
    )

    refund_amount = money(
        refund.amount
    )

    try:
        # Restore the payment value that was reduced
        # when the cash/card/bank refund was posted.
        invoice.paid_amount = money(
            Decimal(invoice.paid_amount)
            + refund_amount
        )

        synchronize_payment_status(
            invoice
        )

        invoice.updated_by_id = (
            current_user.id
        )

        refund.status = (
            RefundStatus.REVERSED.value
        )

        refund.is_reversed = True

        refund.reversed_by_id = (
            current_user.id
        )

        refund.reversed_at = utc_now()

        refund.reversal_reason = (
            payload.reason
        )

        # A completed refund return becomes financially
        # pending again after the refund is reversed.
        if sales_return.status == (
            ReturnStatus.COMPLETED.value
        ):
            old_status = (
                sales_return.status
            )

            sales_return.status = (
                ReturnStatus.PROCESSING.value
            )

            sales_return.completed_at = None

            sales_return.updated_by_id = (
                current_user.id
            )

            await add_status_history(
                session,
                sales_return=sales_return,
                old_status=old_status,
                new_status=(
                    ReturnStatus.PROCESSING.value
                ),
                current_user=current_user,
                remarks=(
                    f"Refund "
                    f"{refund.refund_number} "
                    "reversed: "
                    f"{payload.reason}"
                ),
            )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="refund.reversed",
            module="refunds",
            entity_type="customer_refund",
            entity_id=refund.id,
            entity_reference=(
                refund.refund_number
            ),
            description=(
                f"Customer refund "
                f"{refund.refund_number} "
                "reversed"
            ),
            before_data={
                "refund":
                    refund_before_snapshot,
                "invoice":
                    invoice_before_snapshot,
            },
            after_data={
                "refund":
                    refund_audit_snapshot(
                        refund
                    ),
                "invoice":
                    invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "credit_note_id":
                    refund.credit_note_id,
                "return_id":
                    refund.return_id,
                "reversal_reason":
                    payload.reason,
            },
        )

        await session.commit()
        await session.refresh(refund)

    except Exception:
        await session.rollback()
        raise

    return refund


async def reverse_credit_note(
    session: AsyncSession,
    credit_note_id: int,
    payload: FinancialReversalRequest,
    current_user: User,
) -> CreditNote:
    credit_note = await get_credit_note(
        session,
        credit_note_id,
    )

    if credit_note.is_reversed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This credit note has already "
                "been reversed"
            ),
        )

    if credit_note.status != (
        CreditNoteStatus.POSTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only posted credit notes "
                "can be reversed"
            ),
        )

    active_refunds = await active_refund_total(
        session,
        credit_note.id,
    )

    if active_refunds > ZERO_2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Credit note cannot be reversed "
                "while it has active refunds. "
                "Reverse the refunds first."
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        credit_note.invoice_id,
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    customer = await session.get(
        Customer,
        credit_note.customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer was not found",
        )

    sales_return = await session.get(
        SalesReturn,
        credit_note.return_id,
    )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    credit_amount = money(
        credit_note.amount
    )

    current_credited_amount = money(
        invoice.credited_amount
    )

    if current_credited_amount < credit_amount:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invoice credited amount is "
                "inconsistent with this credit note"
            ),
        )

    invoice_before_snapshot = (
        invoice_audit_snapshot(
            invoice
        )
    )

    credit_note_before_snapshot = (
        credit_note_audit_snapshot(
            credit_note
        )
    )

    old_balance = money(
        invoice.balance_amount
    )

    try:
        invoice.credited_amount = money(
            current_credited_amount
            - credit_amount
        )

        synchronize_payment_status(
            invoice
        )

        new_balance = money(
            invoice.balance_amount
        )

        receivable_increase = money(
            new_balance - old_balance
        )

        if receivable_increase > ZERO_2:
            customer.current_balance = money(
                Decimal(customer.current_balance)
                + receivable_increase
            )

        invoice.updated_by_id = (
            current_user.id
        )

        credit_note.status = (
            CreditNoteStatus.REVERSED.value
        )

        credit_note.is_reversed = True

        credit_note.reversed_by_id = (
            current_user.id
        )

        credit_note.reversed_at = utc_now()

        credit_note.reversal_reason = (
            payload.reason
        )

        await reverse_returned_stock(
            session=session,
            sales_return=sales_return,
            current_user=current_user,
        )

        old_return_status = (
            sales_return.status
        )

        if sales_return.status in {
            ReturnStatus.PROCESSING.value,
            ReturnStatus.COMPLETED.value,
        }:
            sales_return.status = (
                ReturnStatus.APPROVED.value
            )

            sales_return.completed_at = None

            sales_return.updated_by_id = (
                current_user.id
            )

            await add_status_history(
                session,
                sales_return=sales_return,
                old_status=old_return_status,
                new_status=(
                    ReturnStatus.APPROVED.value
                ),
                current_user=current_user,
                remarks=(
                    f"Credit note "
                    f"{credit_note.credit_note_number} "
                    "reversed: "
                    f"{payload.reason}"
                ),
            )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="credit_note.reversed",
            module="credit_notes",
            entity_type="credit_note",
            entity_id=credit_note.id,
            entity_reference=(
                credit_note.credit_note_number
            ),
            description=(
                f"Credit note "
                f"{credit_note.credit_note_number} "
                "reversed"
            ),
            before_data={
                "credit_note":
                    credit_note_before_snapshot,
                "invoice":
                    invoice_before_snapshot,
            },
            after_data={
                "credit_note":
                    credit_note_audit_snapshot(
                        credit_note
                    ),
                "invoice":
                    invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "return_id":
                    credit_note.return_id,
                "customer_id":
                    credit_note.customer_id,
                "reversal_reason":
                    payload.reason,
            },
        )

        await session.commit()
        await session.refresh(credit_note)

    except Exception:
        await session.rollback()
        raise

    return credit_note


async def list_credit_notes(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    credit_note_status: str | None,
) -> dict:
    filters = []

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                CreditNote
                .credit_note_number.ilike(
                    pattern
                ),
                Customer.full_name.ilike(
                    pattern
                ),
                SalesInvoice
                .invoice_number.ilike(
                    pattern
                ),
            )
        )

    if credit_note_status is not None:
        filters.append(
            CreditNote.status
            == credit_note_status
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(CreditNote)
            .join(
                Customer,
                Customer.id
                == CreditNote.customer_id,
            )
            .join(
                SalesInvoice,
                SalesInvoice.id
                == CreditNote.invoice_id,
            )
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(CreditNote)
        .options(
            selectinload(
                CreditNote.refunds
            )
        )
        .join(
            Customer,
            Customer.id
            == CreditNote.customer_id,
        )
        .join(
            SalesInvoice,
            SalesInvoice.id
            == CreditNote.invoice_id,
        )
        .where(*filters)
        .order_by(
            CreditNote.id.desc()
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    records = (
        result.scalars().unique().all()
    )

    return {
        "items": [
            await build_credit_note_detail(
                session,
                record,
            )
            for record in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            ceil(total / page_size)
            if total
            else 0
        ),
    }
