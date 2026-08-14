from __future__ import annotations

import calendar
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from math import ceil

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from sqlalchemy.orm import (
    selectinload,
)

from app.models import (
    CreditNote,
    CreditNoteStatus,
    Customer,
    CustomerPayment,
    CustomerRefund,
    InstallmentFrequency,
    InstallmentPaymentAllocation,
    InstallmentPlan,
    InstallmentPlanStatus,
    InstallmentSchedule,
    InstallmentScheduleStatus,
    InvoiceStatus,
    PaymentStatus,
    RefundStatus,
    SalesInvoice,
    User,
)
from app.schemas.installment import (
    CustomerLedgerEntryResponse,
    CustomerLedgerResponse,
    CustomerStatementResponse,
    InstallmentPaymentCreate,
    InstallmentPaymentResponse,
    InstallmentPaymentReverse,
    InstallmentPlanCancel,
    InstallmentPlanCreate,
    InstallmentPlanDetailResponse,
    InstallmentPlanListResponse,
    InstallmentPlanSummaryResponse,
    InstallmentScheduleResponse,
)
from app.services.audit import (
    create_audit_log,
)


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(value).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def add_months(
    value: date,
    months: int,
) -> date:
    month_index = (
        value.month - 1 + months
    )

    year = (
        value.year
        + month_index // 12
    )

    month = (
        month_index % 12
        + 1
    )

    day = min(
        value.day,
        calendar.monthrange(
            year,
            month,
        )[1],
    )

    return date(
        year,
        month,
        day,
    )


def schedule_due_date(
    first_due_date: date,
    frequency: str,
    index: int,
) -> date:
    if frequency == (
        InstallmentFrequency
        .WEEKLY
        .value
    ):
        return (
            first_due_date
            + timedelta(
                days=7 * index
            )
        )

    if frequency == (
        InstallmentFrequency
        .BIWEEKLY
        .value
    ):
        return (
            first_due_date
            + timedelta(
                days=14 * index
            )
        )

    if frequency == (
        InstallmentFrequency
        .MONTHLY
        .value
    ):
        return add_months(
            first_due_date,
            index,
        )

    raise HTTPException(
        status_code=(
            status
            .HTTP_422_UNPROCESSABLE_CONTENT
        ),
        detail=(
            "Unsupported installment frequency"
        ),
    )


async def get_customer_or_404(
    session: AsyncSession,
    customer_id: int,
) -> Customer:
    result = await session.execute(
        select(Customer).where(
            Customer.id
            == customer_id
        )
    )

    customer = (
        result.scalar_one_or_none()
    )

    if customer is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Customer was not found",
        )

    return customer


async def get_invoice_or_404(
    session: AsyncSession,
    invoice_id: int,
) -> SalesInvoice:
    result = await session.execute(
        select(SalesInvoice)
        .where(
            SalesInvoice.id
            == invoice_id
        )
        .with_for_update()
    )

    invoice = (
        result.scalar_one_or_none()
    )

    if invoice is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Sales invoice was not found"
            ),
        )

    return invoice


async def get_plan_or_404(
    session: AsyncSession,
    plan_id: int,
    *,
    for_update: bool = False,
) -> InstallmentPlan:
    statement = (
        select(InstallmentPlan)
        .options(
            selectinload(
                InstallmentPlan.schedules
            ),
            selectinload(
                InstallmentPlan.allocations
            ),
        )
        .where(
            InstallmentPlan.id
            == plan_id
        )
    )

    if for_update:
        statement = (
            statement.with_for_update()
        )

    result = await session.execute(
        statement
    )

    plan = (
        result.scalar_one_or_none()
    )

    if plan is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Installment plan was not found"
            ),
        )

    return plan


async def get_active_plan_for_invoice(
    session: AsyncSession,
    invoice_id: int,
) -> InstallmentPlan | None:
    result = await session.execute(
        select(InstallmentPlan)
        .options(
            selectinload(
                InstallmentPlan.schedules
            ),
        )
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
    )

    return (
        result.scalar_one_or_none()
    )


def schedule_state(
    schedule: InstallmentSchedule,
    *,
    grace_days: int,
) -> tuple[
    Decimal,
    bool,
    int,
]:
    remaining = money(
        max(
            ZERO,
            Decimal(
                schedule.amount_due
            )
            - Decimal(
                schedule.amount_paid
            ),
        )
    )

    overdue_cutoff = (
        schedule.due_date
        + timedelta(
            days=grace_days
        )
    )

    today = date.today()

    is_overdue = (
        remaining > ZERO
        and today > overdue_cutoff
    )

    days_overdue = (
        max(
            0,
            (
                today
                - overdue_cutoff
            ).days,
        )
        if is_overdue
        else 0
    )

    return (
        remaining,
        is_overdue,
        days_overdue,
    )


def installment_audit_snapshot(
    plan: InstallmentPlan,
) -> dict:
    return {
        "plan_id":
            plan.id,
        "agreement_number":
            plan.agreement_number,
        "invoice_id":
            plan.invoice_id,
        "customer_id":
            plan.customer_id,
        "principal_amount":
            str(
                money(
                    plan.principal_amount
                )
            ),
        "interest_rate":
            str(
                Decimal(
                    plan.interest_rate
                ).quantize(
                    Decimal("0.0001")
                )
            ),
        "interest_amount":
            str(
                money(
                    plan.interest_amount
                )
            ),
        "financed_amount":
            str(
                money(
                    plan.financed_amount
                )
            ),
        "total_paid":
            str(
                money(
                    plan.total_paid
                )
            ),
        "outstanding_amount":
            str(
                money(
                    plan.outstanding_amount
                )
            ),
        "status":
            plan.status,
    }


async def build_plan_summary(
    session: AsyncSession,
    plan: InstallmentPlan,
) -> InstallmentPlanSummaryResponse:
    customer = (
        await get_customer_or_404(
            session,
            plan.customer_id,
        )
    )

    invoice = (
        await get_invoice_or_404(
            session,
            plan.invoice_id,
        )
    )

    overdue_count = 0
    overdue_amount = ZERO

    next_due_date = None
    next_due_amount = None

    for schedule in sorted(
        plan.schedules,
        key=lambda item: (
            item.installment_number
        ),
    ):
        (
            remaining,
            is_overdue,
            _,
        ) = schedule_state(
            schedule,
            grace_days=plan.grace_days,
        )

        if is_overdue:
            overdue_count += 1
            overdue_amount = money(
                overdue_amount
                + remaining
            )

        if (
            next_due_date is None
            and remaining > ZERO
        ):
            next_due_date = (
                schedule.due_date
            )
            next_due_amount = remaining

    if plan.agreement_number is None:
        raise RuntimeError(
            "Agreement number missing"
        )

    if invoice.invoice_number is None:
        raise RuntimeError(
            "Invoice number missing"
        )

    return (
        InstallmentPlanSummaryResponse(
            id=plan.id,
            agreement_number=(
                plan.agreement_number
            ),
            customer_id=(
                plan.customer_id
            ),
            customer_name=(
                customer.full_name
            ),
            invoice_id=plan.invoice_id,
            invoice_number=(
                invoice.invoice_number
            ),
            start_date=(
                plan.start_date
            ),
            first_due_date=(
                plan.first_due_date
            ),
            frequency=plan.frequency,
            installment_count=(
                plan.installment_count
            ),
            principal_amount=money(
                plan.principal_amount
            ),
            interest_rate=Decimal(
                plan.interest_rate
            ).quantize(
                Decimal("0.0001")
            ),
            interest_amount=money(
                plan.interest_amount
            ),
            financed_amount=money(
                plan.financed_amount
            ),
            scheduled_installment_amount=money(
                plan
                .scheduled_installment_amount
            ),
            total_paid=money(
                plan.total_paid
            ),
            outstanding_amount=money(
                plan.outstanding_amount
            ),
            grace_days=plan.grace_days,
            status=plan.status,
            overdue_installment_count=(
                overdue_count
            ),
            overdue_amount=money(
                overdue_amount
            ),
            next_due_date=next_due_date,
            next_due_amount=(
                money(next_due_amount)
                if next_due_amount
                is not None
                else None
            ),
            created_at=plan.created_at,
        )
    )


async def build_plan_detail(
    session: AsyncSession,
    plan: InstallmentPlan,
) -> InstallmentPlanDetailResponse:
    summary = await build_plan_summary(
        session,
        plan,
    )

    schedules = []

    for schedule in sorted(
        plan.schedules,
        key=lambda item: (
            item.installment_number
        ),
    ):
        (
            remaining,
            is_overdue,
            days_overdue,
        ) = schedule_state(
            schedule,
            grace_days=plan.grace_days,
        )

        schedules.append(
            InstallmentScheduleResponse(
                id=schedule.id,
                installment_number=(
                    schedule
                    .installment_number
                ),
                due_date=(
                    schedule.due_date
                ),
                amount_due=money(
                    schedule.amount_due
                ),
                amount_paid=money(
                    schedule.amount_paid
                ),
                remaining_amount=(
                    remaining
                ),
                status=schedule.status,
                is_overdue=is_overdue,
                days_overdue=(
                    days_overdue
                ),
            )
        )

    return InstallmentPlanDetailResponse(
        **summary.model_dump(),
        notes=plan.notes,
        schedules=schedules,
    )


async def create_installment_plan(
    session: AsyncSession,
    payload: InstallmentPlanCreate,
    current_user: User,
) -> InstallmentPlanDetailResponse:
    invoice = await get_invoice_or_404(
        session,
        payload.invoice_id,
    )

    if (
        invoice.invoice_status
        != InvoiceStatus.CONFIRMED.value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Installment plans can only "
                "be created for confirmed invoices"
            ),
        )

    principal_amount = money(
        invoice.balance_amount
    )

    if principal_amount <= ZERO:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "This invoice has no outstanding "
                "balance to finance"
            ),
        )

    interest_rate = Decimal(
        payload.interest_rate
    ).quantize(
        Decimal("0.0001")
    )

    interest_amount = money(
        principal_amount
        * interest_rate
        / Decimal("100")
    )

    financed_amount = money(
        principal_amount
        + interest_amount
    )

    existing_result = (
        await session.execute(
            select(InstallmentPlan)
            .where(
                InstallmentPlan.invoice_id
                == invoice.id
            )
        )
    )

    existing = (
        existing_result
        .scalar_one_or_none()
    )

    if existing is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "An installment plan already "
                "exists for this invoice"
            ),
        )

    customer = (
        await get_customer_or_404(
            session,
            invoice.customer_id,
        )
    )

    installment_count = (
        payload.installment_count
    )

    base_amount = money(
        financed_amount
        / Decimal(
            installment_count
        )
    )

    plan = InstallmentPlan(
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        customer_id=invoice.customer_id,
        invoice_id=invoice.id,
        agreement_number=None,
        start_date=date.today(),
        first_due_date=(
            payload.first_due_date
        ),
        frequency=payload.frequency,
        installment_count=(
            installment_count
        ),
        principal_amount=(
            principal_amount
        ),
        interest_rate=(
            interest_rate
        ),
        interest_amount=(
            interest_amount
        ),
        financed_amount=(
            financed_amount
        ),
        scheduled_installment_amount=(
            base_amount
        ),
        total_paid=ZERO,
        outstanding_amount=(
            financed_amount
        ),
        grace_days=payload.grace_days,
        status=(
            InstallmentPlanStatus
            .ACTIVE
            .value
        ),
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(plan)

    if interest_amount > ZERO:
        customer.current_balance = money(
            Decimal(
                customer.current_balance
            )
            + interest_amount
        )

    try:
        await session.flush()

        plan.agreement_number = (
            f"INS-{plan.id:06d}"
        )

        allocated = ZERO

        for index in range(
            installment_count
        ):
            if (
                index
                == installment_count - 1
            ):
                amount_due = money(
                    financed_amount
                    - allocated
                )
            else:
                amount_due = base_amount

            allocated = money(
                allocated
                + amount_due
            )

            session.add(
                InstallmentSchedule(
                    plan_id=plan.id,
                    installment_number=(
                        index + 1
                    ),
                    due_date=(
                        schedule_due_date(
                            payload
                            .first_due_date,
                            payload.frequency,
                            index,
                        )
                    ),
                    amount_due=amount_due,
                    amount_paid=ZERO,
                    status=(
                        InstallmentScheduleStatus
                        .PENDING
                        .value
                    ),
                )
            )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "installment.plan_created"
            ),
            module="installments",
            entity_type=(
                "installment_plan"
            ),
            entity_id=plan.id,
            entity_reference=(
                plan.agreement_number
            ),
            description=(
                f"Installment plan "
                f"{plan.agreement_number} "
                "created"
            ),
            before_data=None,
            after_data=(
                installment_audit_snapshot(
                    plan
                )
            ),
            metadata={
                "invoice_id":
                    invoice.id,
                "customer_id":
                    customer.id,
                "installment_count":
                    installment_count,
                "frequency":
                    payload.frequency,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    plan = await get_plan_or_404(
        session,
        plan.id,
    )

    return await build_plan_detail(
        session,
        plan,
    )


async def list_installment_plans(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    customer_id: int | None,
    invoice_id: int | None,
    status_filter: str | None,
) -> InstallmentPlanListResponse:
    filters = []

    if customer_id is not None:
        filters.append(
            InstallmentPlan.customer_id
            == customer_id
        )

    if invoice_id is not None:
        filters.append(
            InstallmentPlan.invoice_id
            == invoice_id
        )

    if status_filter is not None:
        filters.append(
            InstallmentPlan.status
            == status_filter
        )

    total = int(
        (
            await session.execute(
                select(
                    func.count(
                        InstallmentPlan.id
                    )
                ).where(*filters)
            )
        ).scalar_one()
    )

    result = await session.execute(
        select(InstallmentPlan)
        .options(
            selectinload(
                InstallmentPlan.schedules
            )
        )
        .where(*filters)
        .order_by(
            InstallmentPlan.id.desc()
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    plans = result.scalars().all()

    return InstallmentPlanListResponse(
        items=[
            await build_plan_summary(
                session,
                plan,
            )
            for plan in plans
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(
            ceil(total / page_size)
            if total
            else 0
        ),
    )


async def read_installment_plan(
    session: AsyncSession,
    plan_id: int,
) -> InstallmentPlanDetailResponse:
    plan = await get_plan_or_404(
        session,
        plan_id,
    )

    return await build_plan_detail(
        session,
        plan,
    )


async def receive_installment_payment(
    session: AsyncSession,
    *,
    plan_id: int,
    payload: InstallmentPaymentCreate,
    current_user: User,
) -> InstallmentPaymentResponse:
    plan = await get_plan_or_404(
        session,
        plan_id,
        for_update=True,
    )

    if (
        plan.status
        != InstallmentPlanStatus
        .ACTIVE
        .value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Payments can only be received "
                "for active installment plans"
            ),
        )

    amount = money(
        payload.amount
    )

    outstanding = money(
        plan.outstanding_amount
    )

    if amount > outstanding:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Payment amount cannot exceed "
                f"installment outstanding "
                f"{outstanding}"
            ),
        )

    invoice = await get_invoice_or_404(
        session,
        plan.invoice_id,
    )

    customer = (
        await get_customer_or_404(
            session,
            plan.customer_id,
        )
    )

    active_allocations = [
        allocation
        for allocation in plan.allocations
        if not allocation.is_reversed
    ]

    paid_principal = money(
        sum(
            (
                Decimal(
                    allocation.principal_amount
                )
                for allocation
                in active_allocations
            ),
            ZERO,
        )
    )

    paid_interest = money(
        sum(
            (
                Decimal(
                    allocation.interest_amount
                )
                for allocation
                in active_allocations
            ),
            ZERO,
        )
    )

    principal_remaining = money(
        max(
            ZERO,
            Decimal(
                plan.principal_amount
            )
            - paid_principal,
        )
    )

    interest_remaining = money(
        max(
            ZERO,
            Decimal(
                plan.interest_amount
            )
            - paid_interest,
        )
    )

    if money(
        invoice.balance_amount
    ) != principal_remaining:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Installment plan and invoice "
                "principal balances are inconsistent"
            ),
        )

    if money(
        principal_remaining
        + interest_remaining
    ) != outstanding:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Installment principal, interest, "
                "and outstanding balances are "
                "inconsistent"
            ),
        )

    # Allocate each payment proportionally across the
    # remaining principal and interest balances.
    #
    # Example:
    # principal remaining = 150,000
    # interest remaining  =  15,000
    # payment             =  55,000
    #
    # principal component = 50,000
    # interest component  =  5,000
    if amount == outstanding:
        principal_component = (
            principal_remaining
        )
        interest_component = (
            interest_remaining
        )
    else:
        principal_component = money(
            amount
            * principal_remaining
            / outstanding
        )

        principal_component = money(
            min(
                principal_component,
                principal_remaining,
            )
        )

        interest_component = money(
            amount
            - principal_component
        )

        if (
            interest_component
            > interest_remaining
        ):
            interest_component = (
                interest_remaining
            )

            principal_component = money(
                amount
                - interest_component
            )

    if (
        principal_component
        > principal_remaining
        or interest_component
        > interest_remaining
        or money(
            principal_component
            + interest_component
        ) != amount
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Installment payment split "
                "is inconsistent"
            ),
        )

    payment = CustomerPayment(
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        receipt_number=None,
        customer_id=customer.id,
        invoice_id=invoice.id,
        amount=amount,
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

    allocations_payload = []

    try:
        await session.flush()

        payment.receipt_number = (
            f"REC-{payment.id:06d}"
        )

        remaining_payment = amount

        remaining_principal_component = (
            principal_component
        )

        remaining_interest_component = (
            interest_component
        )

        schedules = sorted(
            plan.schedules,
            key=lambda item: (
                item.installment_number
            ),
        )

        for schedule in schedules:
            if remaining_payment <= ZERO:
                break

            schedule_remaining = money(
                max(
                    ZERO,
                    Decimal(
                        schedule.amount_due
                    )
                    - Decimal(
                        schedule.amount_paid
                    ),
                )
            )

            if schedule_remaining <= ZERO:
                continue

            allocation_amount = money(
                min(
                    remaining_payment,
                    schedule_remaining,
                )
            )

            schedule.amount_paid = money(
                Decimal(
                    schedule.amount_paid
                )
                + allocation_amount
            )

            if (
                money(schedule.amount_paid)
                >= money(
                    schedule.amount_due
                )
            ):
                schedule.amount_paid = money(
                    schedule.amount_due
                )
                schedule.status = (
                    InstallmentScheduleStatus
                    .PAID
                    .value
                )
            elif schedule.amount_paid > ZERO:
                schedule.status = (
                    InstallmentScheduleStatus
                    .PARTIAL
                    .value
                )

            # Preserve the same proportional principal /
            # interest split when one payment spans one or
            # more installment schedules.
            #
            # The final allocation consumes the exact
            # remaining components so rounding differences
            # cannot accumulate.
            if (
                allocation_amount
                == remaining_payment
            ):
                allocation_principal = (
                    remaining_principal_component
                )
                allocation_interest = (
                    remaining_interest_component
                )
            else:
                allocation_principal = money(
                    allocation_amount
                    * remaining_principal_component
                    / remaining_payment
                )

                allocation_principal = money(
                    min(
                        allocation_principal,
                        remaining_principal_component,
                    )
                )

                allocation_interest = money(
                    allocation_amount
                    - allocation_principal
                )

                if (
                    allocation_interest
                    > remaining_interest_component
                ):
                    allocation_interest = (
                        remaining_interest_component
                    )

                    allocation_principal = money(
                        allocation_amount
                        - allocation_interest
                    )

            remaining_principal_component = money(
                remaining_principal_component
                - allocation_principal
            )

            remaining_interest_component = money(
                remaining_interest_component
                - allocation_interest
            )

            allocation = (
                InstallmentPaymentAllocation(
                    plan_id=plan.id,
                    schedule_id=(
                        schedule.id
                    ),
                    payment_id=(
                        payment.id
                    ),
                    amount=(
                        allocation_amount
                    ),
                    principal_amount=(
                        allocation_principal
                    ),
                    interest_amount=(
                        allocation_interest
                    ),
                    is_reversed=False,
                )
            )

            session.add(allocation)

            allocations_payload.append(
                {
                    "schedule_id":
                        schedule.id,
                    "installment_number":
                        schedule
                        .installment_number,
                    "amount":
                        str(
                            allocation_amount
                        ),
                    "principal_amount":
                        str(
                            allocation_principal
                        ),
                    "interest_amount":
                        str(
                            allocation_interest
                        ),
                }
            )

            remaining_payment = money(
                remaining_payment
                - allocation_amount
            )

        if remaining_payment != ZERO:
            raise RuntimeError(
                "Installment payment could not "
                "be fully allocated"
            )

        if (
            remaining_principal_component
            != ZERO
            or remaining_interest_component
            != ZERO
        ):
            raise RuntimeError(
                "Installment principal/interest "
                "split could not be fully allocated"
            )

        plan.total_paid = money(
            Decimal(plan.total_paid)
            + amount
        )

        plan.outstanding_amount = money(
            max(
                ZERO,
                Decimal(
                    plan.financed_amount
                )
                - Decimal(
                    plan.total_paid
                ),
            )
        )

        invoice.paid_amount = money(
            Decimal(
                invoice.paid_amount
            )
            + principal_component
        )

        invoice.balance_amount = money(
            max(
                ZERO,
                Decimal(
                    invoice.grand_total
                )
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
                - amount,
            )
        )

        if (
            plan.outstanding_amount
            == ZERO
        ):
            plan.status = (
                InstallmentPlanStatus
                .COMPLETED
                .value
            )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "installment.payment_received"
            ),
            module="installments",
            entity_type=(
                "customer_payment"
            ),
            entity_id=payment.id,
            entity_reference=(
                payment.receipt_number
            ),
            description=(
                f"Installment payment "
                f"{payment.receipt_number} "
                "received"
            ),
            before_data=None,
            after_data={
                "plan":
                    installment_audit_snapshot(
                        plan
                    ),
                "payment": {
                    "payment_id":
                        payment.id,
                    "amount":
                        str(amount),
                    "principal_amount":
                        str(
                            principal_component
                        ),
                    "interest_amount":
                        str(
                            interest_component
                        ),
                    "receipt_number":
                        payment
                        .receipt_number,
                },
            },
            metadata={
                "plan_id":
                    plan.id,
                "invoice_id":
                    invoice.id,
                "customer_id":
                    customer.id,
                "allocations":
                    allocations_payload,
            },
        )

        await session.commit()

        await session.refresh(
            payment
        )
        await session.refresh(
            invoice
        )
        await session.refresh(
            customer
        )

    except Exception:
        await session.rollback()
        raise

    if (
        payment.receipt_number
        is None
        or plan.agreement_number
        is None
        or invoice.invoice_number
        is None
    ):
        raise RuntimeError(
            "Generated reference missing"
        )

    return InstallmentPaymentResponse(
        message=(
            "Installment payment recorded "
            "successfully"
        ),
        payment_id=payment.id,
        receipt_number=(
            payment.receipt_number
        ),
        plan_id=plan.id,
        agreement_number=(
            plan.agreement_number
        ),
        invoice_id=invoice.id,
        invoice_number=(
            invoice.invoice_number
        ),
        customer_id=customer.id,
        amount=amount,
        principal_amount=(
            principal_component
        ),
        interest_amount=(
            interest_component
        ),
        payment_method=(
            payment.payment_method
        ),
        plan_total_paid=money(
            plan.total_paid
        ),
        plan_outstanding_amount=money(
            plan.outstanding_amount
        ),
        invoice_paid_amount=money(
            invoice.paid_amount
        ),
        invoice_balance_amount=money(
            invoice.balance_amount
        ),
        customer_balance=money(
            customer.current_balance
        ),
        allocations=allocations_payload,
    )


async def reverse_installment_payment(
    session: AsyncSession,
    *,
    plan_id: int,
    payment_id: int,
    payload: InstallmentPaymentReverse,
    current_user: User,
) -> InstallmentPaymentResponse:
    plan = await get_plan_or_404(
        session,
        plan_id,
        for_update=True,
    )

    payment_result = (
        await session.execute(
            select(CustomerPayment)
            .where(
                CustomerPayment.id
                == payment_id,
                CustomerPayment.invoice_id
                == plan.invoice_id,
                CustomerPayment.customer_id
                == plan.customer_id,
            )
            .with_for_update()
        )
    )

    payment = (
        payment_result.scalar_one_or_none()
    )

    if payment is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Installment payment "
                "was not found"
            ),
        )

    if payment.is_reversed:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "This payment has already "
                "been reversed"
            ),
        )

    allocation_result = (
        await session.execute(
            select(
                InstallmentPaymentAllocation
            )
            .where(
                InstallmentPaymentAllocation
                .plan_id
                == plan.id,
                InstallmentPaymentAllocation
                .payment_id
                == payment.id,
                InstallmentPaymentAllocation
                .is_reversed
                .is_(False),
            )
        )
    )

    allocations = (
        allocation_result.scalars().all()
    )

    if not allocations:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "This payment is not an "
                "installment-plan payment"
            ),
        )

    invoice = await get_invoice_or_404(
        session,
        plan.invoice_id,
    )

    customer = (
        await get_customer_or_404(
            session,
            plan.customer_id,
        )
    )

    payment_amount = money(
        payment.amount
    )

    principal_component = money(
        sum(
            (
                Decimal(
                    allocation.principal_amount
                )
                for allocation in allocations
            ),
            ZERO,
        )
    )

    interest_component = money(
        sum(
            (
                Decimal(
                    allocation.interest_amount
                )
                for allocation in allocations
            ),
            ZERO,
        )
    )

    if money(
        principal_component
        + interest_component
    ) != payment_amount:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Stored installment payment split "
                "does not match payment amount"
            ),
        )

    if principal_component > money(
        invoice.paid_amount
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Payment reversal would make "
                "invoice paid amount negative"
            ),
        )

    if payment_amount > money(
        plan.total_paid
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Payment reversal would make "
                "plan paid amount negative"
            ),
        )

    allocation_payload = []

    try:
        for allocation in allocations:
            schedule_result = (
                await session.execute(
                    select(
                        InstallmentSchedule
                    )
                    .where(
                        InstallmentSchedule.id
                        == allocation.schedule_id
                    )
                    .with_for_update()
                )
            )

            schedule = (
                schedule_result
                .scalar_one()
            )

            amount = money(
                allocation.amount
            )

            schedule.amount_paid = money(
                max(
                    ZERO,
                    Decimal(
                        schedule.amount_paid
                    )
                    - amount,
                )
            )

            if schedule.amount_paid == ZERO:
                schedule.status = (
                    InstallmentScheduleStatus
                    .PENDING
                    .value
                )
            elif (
                schedule.amount_paid
                < schedule.amount_due
            ):
                schedule.status = (
                    InstallmentScheduleStatus
                    .PARTIAL
                    .value
                )
            else:
                schedule.status = (
                    InstallmentScheduleStatus
                    .PAID
                    .value
                )

            allocation.is_reversed = True

            allocation_payload.append(
                {
                    "schedule_id":
                        schedule.id,
                    "installment_number":
                        schedule
                        .installment_number,
                    "amount":
                        str(amount),
                    "principal_amount":
                        str(
                            money(
                                allocation
                                .principal_amount
                            )
                        ),
                    "interest_amount":
                        str(
                            money(
                                allocation
                                .interest_amount
                            )
                        ),
                }
            )

        payment.is_reversed = True
        payment.reversed_at = utc_now()
        payment.reversal_reason = (
            payload.reason.strip()
        )

        plan.total_paid = money(
            Decimal(plan.total_paid)
            - payment_amount
        )

        plan.outstanding_amount = money(
            Decimal(
                plan.financed_amount
            )
            - Decimal(
                plan.total_paid
            )
        )

        if (
            plan.status
            == InstallmentPlanStatus
            .COMPLETED
            .value
        ):
            plan.status = (
                InstallmentPlanStatus
                .ACTIVE
                .value
            )

        invoice.paid_amount = money(
            Decimal(
                invoice.paid_amount
            )
            - principal_component
        )

        invoice.balance_amount = money(
            max(
                ZERO,
                Decimal(
                    invoice.grand_total
                )
                - Decimal(
                    invoice.credited_amount
                )
                - Decimal(
                    invoice.paid_amount
                ),
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

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "installment.payment_reversed"
            ),
            module="installments",
            entity_type=(
                "customer_payment"
            ),
            entity_id=payment.id,
            entity_reference=(
                payment.receipt_number
            ),
            description=(
                f"Installment payment "
                f"{payment.receipt_number} "
                "reversed"
            ),
            before_data=None,
            after_data={
                "plan":
                    installment_audit_snapshot(
                        plan
                    ),
                "payment": {
                    "payment_id":
                        payment.id,
                    "principal_amount":
                        str(
                            principal_component
                        ),
                    "interest_amount":
                        str(
                            interest_component
                        ),
                    "is_reversed":
                        True,
                },
            },
            metadata={
                "reason":
                    payload.reason.strip(),
                "allocations":
                    allocation_payload,
            },
        )

        await session.commit()

        await session.refresh(
            payment
        )
        await session.refresh(
            invoice
        )
        await session.refresh(
            customer
        )

    except Exception:
        await session.rollback()
        raise

    if (
        payment.receipt_number
        is None
        or plan.agreement_number
        is None
        or invoice.invoice_number
        is None
    ):
        raise RuntimeError(
            "Reference missing"
        )

    return InstallmentPaymentResponse(
        message=(
            "Installment payment reversed "
            "successfully"
        ),
        payment_id=payment.id,
        receipt_number=(
            payment.receipt_number
        ),
        plan_id=plan.id,
        agreement_number=(
            plan.agreement_number
        ),
        invoice_id=invoice.id,
        invoice_number=(
            invoice.invoice_number
        ),
        customer_id=customer.id,
        amount=payment_amount,
        principal_amount=(
            principal_component
        ),
        interest_amount=(
            interest_component
        ),
        payment_method=(
            payment.payment_method
        ),
        plan_total_paid=money(
            plan.total_paid
        ),
        plan_outstanding_amount=money(
            plan.outstanding_amount
        ),
        invoice_paid_amount=money(
            invoice.paid_amount
        ),
        invoice_balance_amount=money(
            invoice.balance_amount
        ),
        customer_balance=money(
            customer.current_balance
        ),
        allocations=allocation_payload,
    )


async def cancel_installment_plan(
    session: AsyncSession,
    *,
    plan_id: int,
    payload: InstallmentPlanCancel,
    current_user: User,
) -> InstallmentPlanDetailResponse:
    plan = await get_plan_or_404(
        session,
        plan_id,
        for_update=True,
    )

    if (
        plan.status
        != InstallmentPlanStatus
        .ACTIVE
        .value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Only active installment "
                "plans can be cancelled"
            ),
        )

    active_allocations = [
        allocation
        for allocation in plan.allocations
        if not allocation.is_reversed
    ]

    if active_allocations:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Reverse installment payments "
                "before cancelling the plan"
            ),
        )

    before = (
        installment_audit_snapshot(
            plan
        )
    )

    try:
        plan.status = (
            InstallmentPlanStatus
            .CANCELLED
            .value
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "installment.plan_cancelled"
            ),
            module="installments",
            entity_type=(
                "installment_plan"
            ),
            entity_id=plan.id,
            entity_reference=(
                plan.agreement_number
            ),
            description=(
                f"Installment plan "
                f"{plan.agreement_number} "
                "cancelled"
            ),
            before_data=before,
            after_data=(
                installment_audit_snapshot(
                    plan
                )
            ),
            metadata={
                "reason":
                    payload.reason.strip()
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    plan = await get_plan_or_404(
        session,
        plan.id,
    )

    return await build_plan_detail(
        session,
        plan,
    )


async def build_ledger_entries(
    session: AsyncSession,
    customer_id: int,
) -> list[dict]:
    customer = (
        await get_customer_or_404(
            session,
            customer_id,
        )
    )

    entries = []

    invoice_result = (
        await session.execute(
            select(SalesInvoice)
            .where(
                SalesInvoice.customer_id
                == customer.id,
                SalesInvoice.invoice_status
                == InvoiceStatus
                .CONFIRMED
                .value,
            )
        )
    )

    for invoice in (
        invoice_result.scalars().all()
    ):
        if invoice.invoice_number is None:
            continue

        entries.append({
            "transaction_date":
                invoice.invoice_date,
            "transaction_type":
                "sales_invoice",
            "reference":
                invoice.invoice_number,
            "description":
                "Sales invoice",
            "debit":
                money(
                    invoice.grand_total
                ),
            "credit":
                ZERO,
            "invoice_id":
                invoice.id,
            "payment_id":
                None,
            "sort_id":
                invoice.id,
        })

    installment_result = (
        await session.execute(
            select(InstallmentPlan)
            .where(
                InstallmentPlan.customer_id
                == customer.id,
                InstallmentPlan.interest_amount
                > ZERO,
            )
        )
    )

    for plan in (
        installment_result.scalars().all()
    ):
        if plan.agreement_number is None:
            continue

        interest_amount = money(
            plan.interest_amount
        )

        if interest_amount <= ZERO:
            continue

        entries.append({
            "transaction_date":
                plan.created_at,
            "transaction_type":
                "installment_interest",
            "reference":
                plan.agreement_number,
            "description":
                "Installment interest charge",
            "debit":
                interest_amount,
            "credit":
                ZERO,
            "invoice_id":
                plan.invoice_id,
            "payment_id":
                None,
            "sort_id":
                plan.id,
        })

    payment_result = (
        await session.execute(
            select(CustomerPayment)
            .where(
                CustomerPayment.customer_id
                == customer.id,
                CustomerPayment.is_reversed
                .is_(False),
            )
        )
    )

    for payment in (
        payment_result.scalars().all()
    ):
        if payment.receipt_number is None:
            continue

        entries.append({
            "transaction_date":
                payment.payment_date,
            "transaction_type":
                "payment",
            "reference":
                payment.receipt_number,
            "description":
                "Customer payment",
            "debit":
                ZERO,
            "credit":
                money(
                    payment.amount
                ),
            "invoice_id":
                payment.invoice_id,
            "payment_id":
                payment.id,
            "sort_id":
                payment.id,
        })

    credit_result = (
        await session.execute(
            select(CreditNote)
            .where(
                CreditNote.customer_id
                == customer.id,
                CreditNote.status
                == CreditNoteStatus
                .POSTED
                .value,
                CreditNote.is_reversed
                .is_(False),
            )
        )
    )

    for credit_note in (
        credit_result.scalars().all()
    ):
        if (
            credit_note.credit_note_number
            is None
        ):
            continue

        entries.append({
            "transaction_date":
                (
                    credit_note.posted_at
                    or credit_note.created_at
                ),
            "transaction_type":
                "credit_note",
            "reference":
                credit_note
                .credit_note_number,
            "description":
                "Posted credit note",
            "debit":
                ZERO,
            "credit":
                money(
                    credit_note.amount
                ),
            "invoice_id":
                credit_note.invoice_id,
            "payment_id":
                None,
            "sort_id":
                credit_note.id,
        })

    refund_result = (
        await session.execute(
            select(CustomerRefund)
            .where(
                CustomerRefund.customer_id
                == customer.id,
                CustomerRefund.status
                == RefundStatus
                .POSTED
                .value,
                CustomerRefund.is_reversed
                .is_(False),
            )
        )
    )

    for refund in (
        refund_result.scalars().all()
    ):
        if refund.refund_number is None:
            continue

        entries.append({
            "transaction_date":
                (
                    refund.posted_at
                    or refund.created_at
                ),
            "transaction_type":
                "customer_refund",
            "reference":
                refund.refund_number,
            "description":
                "Customer refund",
            "debit":
                money(
                    refund.amount
                ),
            "credit":
                ZERO,
            "invoice_id":
                refund.invoice_id,
            "payment_id":
                None,
            "sort_id":
                refund.id,
        })

    entries.sort(
        key=lambda item: (
            item["transaction_date"],
            item["transaction_type"],
            item["sort_id"],
        )
    )

    return entries


async def customer_ledger(
    session: AsyncSession,
    *,
    customer_id: int,
    date_from: date | None,
    date_to: date | None,
) -> CustomerLedgerResponse:
    customer = (
        await get_customer_or_404(
            session,
            customer_id,
        )
    )

    all_entries = (
        await build_ledger_entries(
            session,
            customer_id,
        )
    )

    opening_balance = ZERO

    filtered = []

    for item in all_entries:
        transaction_date = (
            item["transaction_date"].date()
        )

        if (
            date_from is not None
            and transaction_date
            < date_from
        ):
            opening_balance = money(
                opening_balance
                + item["debit"]
                - item["credit"]
            )

            continue

        if (
            date_to is not None
            and transaction_date
            > date_to
        ):
            continue

        filtered.append(item)

    running = opening_balance

    total_debits = ZERO
    total_credits = ZERO

    response_entries = []

    for item in filtered:
        total_debits = money(
            total_debits
            + item["debit"]
        )

        total_credits = money(
            total_credits
            + item["credit"]
        )

        running = money(
            running
            + item["debit"]
            - item["credit"]
        )

        response_entries.append(
            CustomerLedgerEntryResponse(
                transaction_date=(
                    item[
                        "transaction_date"
                    ]
                ),
                transaction_type=(
                    item[
                        "transaction_type"
                    ]
                ),
                reference=(
                    item["reference"]
                ),
                description=(
                    item["description"]
                ),
                debit=(
                    item["debit"]
                ),
                credit=(
                    item["credit"]
                ),
                running_balance=running,
                invoice_id=(
                    item["invoice_id"]
                ),
                payment_id=(
                    item["payment_id"]
                ),
            )
        )

    return CustomerLedgerResponse(
        customer_id=customer.id,
        customer_number=(
            customer.customer_number
        ),
        customer_name=(
            customer.full_name
        ),
        opening_balance=(
            opening_balance
        ),
        total_debits=(
            total_debits
        ),
        total_credits=(
            total_credits
        ),
        closing_balance=running,
        date_from=date_from,
        date_to=date_to,
        entries=response_entries,
    )


async def customer_statement(
    session: AsyncSession,
    *,
    customer_id: int,
    date_from: date | None,
    date_to: date | None,
) -> CustomerStatementResponse:
    ledger = await customer_ledger(
        session,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )

    return CustomerStatementResponse(
        **ledger.model_dump(),
        generated_at=utc_now(),
    )
