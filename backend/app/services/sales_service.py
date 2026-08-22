from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.audit import create_audit_log
from app.models import (
    Branch,
    Company,
    Customer,
    CustomerPayment,
    InvoiceStatus,
    PaymentStatus,
    Product,
    ProductSerialNumber,
    SalesInvoice,
    SalesInvoiceItem,
    SalesTradeIn,
    SerialNumberStatus,
    StockItem,
    StockMovement,
    StockMovementType,
    User,
    Warehouse,
)
from app.models.sales import (
    InvoiceItemType,
    InvoiceSourceType,
)
from app.models.service import (
    ServiceJobCard,
    ServiceJobPart,
    ServiceJobStatus,
    ServiceLabourItem,
)
from app.schemas.sales import (
    PaymentCreate,
    SalesInvoiceConfirmRequest,
    SalesInvoiceCreate,
    SalesInvoiceDetailResponse,
    SalesInvoiceListResponse,
    SalesInvoiceResponse,
)


ZERO_2 = Decimal("0.00")
ZERO_3 = Decimal("0.000")
ONE_3 = Decimal("1.000")


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        Decimal("0.01")
    )



def sales_invoice_audit_snapshot(
    invoice: SalesInvoice,
) -> dict:
    return {
        "invoice_id":
            invoice.id,
        "invoice_number":
            invoice.invoice_number,
        "company_id":
            invoice.company_id,
        "branch_id":
            invoice.branch_id,
        "customer_id":
            invoice.customer_id,
        "source_type":
            invoice.source_type,
        "source_id":
            invoice.source_id,
        "subtotal":
            str(money(invoice.subtotal)),
        "discount_amount":
            str(money(invoice.discount_amount)),
        "tax_amount":
            str(money(invoice.tax_amount)),
        "grand_total":
            str(money(invoice.grand_total)),
        "credited_amount":
            str(money(invoice.credited_amount)),
        "trade_in_amount":
            str(money(invoice.trade_in_amount)),
        "paid_amount":
            str(money(invoice.paid_amount)),
        "balance_amount":
            str(money(invoice.balance_amount)),
        "payment_status":
            invoice.payment_status,
        "invoice_status":
            invoice.invoice_status,
    }


def sales_customer_audit_snapshot(
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
            str(money(customer.current_balance)),
    }


def sales_payment_audit_snapshot(
    payment: CustomerPayment,
) -> dict:
    return {
        "payment_id":
            payment.id,
        "receipt_number":
            payment.receipt_number,
        "invoice_id":
            payment.invoice_id,
        "customer_id":
            payment.customer_id,
        "amount":
            str(money(payment.amount)),
        "payment_method":
            payment.payment_method,
        "reference_number":
            payment.reference_number,
        "is_reversed":
            payment.is_reversed,
    }


def add_months(
    source_date: date,
    months: int,
) -> date:
    month_index = (
        source_date.month - 1 + months
    )

    year = (
        source_date.year
        + month_index // 12
    )

    month = (
        month_index % 12 + 1
    )

    day = min(
        source_date.day,
        calendar.monthrange(year, month)[1],
    )

    return date(year, month, day)


async def get_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(
            Company.is_active.is_(True)
        )
        .order_by(Company.id)
    )

    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active company is not configured",
        )

    return company


async def get_branch(
    session: AsyncSession,
    branch_id: int | None,
) -> Branch:
    if branch_id is not None:
        branch = await session.get(
            Branch,
            branch_id,
        )
    else:
        result = await session.execute(
            select(Branch)
            .where(
                Branch.is_main_branch.is_(True),
                Branch.is_active.is_(True),
            )
            .order_by(Branch.id)
        )

        branch = result.scalars().first()

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Active sales branch is not configured"
            ),
        )

    if not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected branch is inactive",
        )

    return branch


async def get_customer(
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

    if customer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected customer is not active",
        )

    return customer


async def get_invoice(
    session: AsyncSession,
    invoice_id: int,
) -> SalesInvoice:
    result = await session.execute(
        select(SalesInvoice)
        .options(
            selectinload(
                SalesInvoice.items
            ),
            selectinload(
                SalesInvoice.payments
            ),
            selectinload(
                SalesInvoice.trade_ins
            ),
        )
        .where(
            SalesInvoice.id == invoice_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    return invoice


async def get_service_job(
    session: AsyncSession,
    job_id: int,
) -> ServiceJobCard:
    result = await session.execute(
        select(ServiceJobCard)
        .options(
            selectinload(
                ServiceJobCard.parts
            ),
            selectinload(
                ServiceJobCard.labour_items
            ),
        )
        .where(
            ServiceJobCard.id == job_id
        )
    )

    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service job card was not found",
        )

    return job


async def create_draft_invoice(
    session: AsyncSession,
    payload: SalesInvoiceCreate,
    current_user: User,
) -> SalesInvoice:
    company = await get_company(session)

    branch = await get_branch(
        session,
        payload.branch_id,
    )

    customer = await get_customer(
        session,
        payload.customer_id,
    )

    if branch.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Branch belongs to another company",
        )

    invoice_source_type = (
        InvoiceSourceType.SALES.value
    )
    invoice_source_id = None

    if payload.source_type is not None:
        requested_source_type = (
            payload.source_type
            .strip()
            .lower()
        )

        if (
            requested_source_type
            != InvoiceSourceType
            .LEGACY_SERVICE_JOB
            .value
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Unsupported sales invoice source type"
                ),
            )

        if payload.source_id is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Legacy service job source_id "
                    "is required"
                ),
            )

        from app.models.legacy_service_job import (
            LegacyServiceJob,
        )

        legacy_source = (
            await session.execute(
                select(
                    LegacyServiceJob
                ).where(
                    LegacyServiceJob.legacy_job_id
                    == payload.source_id
                )
            )
        ).scalar_one_or_none()

        if legacy_source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Legacy service job source "
                    "was not found"
                ),
            )

        invoice_source_type = (
            InvoiceSourceType
            .LEGACY_SERVICE_JOB
            .value
        )

        invoice_source_id = (
            legacy_source.legacy_job_id
        )

    elif payload.source_id is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "source_type is required "
                "when source_id is supplied"
            ),
        )

    subtotal = ZERO_2
    prepared_items = []

    for item in payload.items:
        product = await session.get(
            Product,
            item.product_id,
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Product {item.product_id} "
                    "was not found"
                ),
            )

        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Product {product.product_code} "
                    "is inactive"
                ),
            )

        if (
            item.unit_price
            < product.minimum_selling_price
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{product.product_code}: "
                    "unit price is below minimum "
                    "selling price"
                ),
            )

        gross = money(
            item.quantity
            * item.unit_price
        )

        line_total = money(
            gross
            - item.discount_amount
        )

        subtotal += line_total

        if product.track_serial_numbers:
            if item.serial_number_id is None:
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_CONTENT
                    ),
                    detail=(
                        f"{product.product_code} "
                        "requires a serial number"
                    ),
                )

            if item.quantity != ONE_3:
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_CONTENT
                    ),
                    detail=(
                        "Serialized invoice item "
                        "quantity must be exactly 1"
                    ),
                )

        elif item.serial_number_id is not None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    f"{product.product_code} does not "
                    "use serial tracking"
                ),
            )

        prepared_items.append(
            (
                item,
                product,
                line_total,
            )
        )

    subtotal = money(subtotal)

    if (
        payload.invoice_discount_amount
        > subtotal
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Invoice discount cannot exceed subtotal"
            ),
        )

    grand_total = money(
        subtotal
        - payload.invoice_discount_amount
        + payload.tax_amount
    )

    trade_in_total = money(
        sum(
            (
                Decimal(
                    trade_in.allowance_amount
                )
                for trade_in
                in payload.trade_ins
            ),
            ZERO_2,
        )
    )

    if trade_in_total > grand_total:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Trade-in allowance cannot exceed "
                "the invoice grand total"
            ),
        )

    invoice = SalesInvoice(
        company_id=company.id,
        branch_id=branch.id,
        invoice_number=None,
        customer_id=customer.id,
        source_type=invoice_source_type,
        source_id=invoice_source_id,
        subtotal=subtotal,
        discount_amount=(
            payload.invoice_discount_amount
        ),
        tax_amount=payload.tax_amount,
        grand_total=grand_total,
        trade_in_amount=trade_in_total,
        paid_amount=ZERO_2,
        balance_amount=money(
            grand_total - trade_in_total
        ),
        payment_status=(
            PaymentStatus.UNPAID.value
        ),
        invoice_status=(
            InvoiceStatus.DRAFT.value
        ),
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(invoice)
    await session.flush()

    invoice.invoice_number = (
        f"INV-{invoice.id:06d}"
    )

    for trade_in in payload.trade_ins:
        session.add(
            SalesTradeIn(
                invoice_id=invoice.id,
                brand=trade_in.brand,
                model=trade_in.model,
                serial_number=(
                    trade_in.serial_number
                ),
                condition=trade_in.condition,
                description=(
                    trade_in.description
                ),
                allowance_amount=money(
                    trade_in.allowance_amount
                ),
            )
        )

    for (
        item,
        product,
        line_total,
    ) in prepared_items:
        session.add(
            SalesInvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                warehouse_id=item.warehouse_id,
                item_type=(
                    InvoiceItemType.PRODUCT.value
                ),
                serial_number_id=(
                    item.serial_number_id
                ),
                description=(
                    item.description
                    or product.name
                ),
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=(
                    item.discount_amount
                ),
                line_total=line_total,
            )
        )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="sales.invoice_draft_created",
            module="sales",
            entity_type="sales_invoice",
            entity_id=invoice.id,
            entity_reference=(
                invoice.invoice_number
            ),
            description=(
                f"Sales invoice "
                f"{invoice.invoice_number} "
                "draft created"
            ),
            before_data=None,
            after_data={
                "invoice":
                    sales_invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "customer_id":
                    invoice.customer_id,
                "branch_id":
                    invoice.branch_id,
                "source_type":
                    invoice.source_type,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_invoice(
        session,
        invoice.id,
    )


async def create_service_job_invoice(
    session: AsyncSession,
    job_id: int,
    current_user: User,
    due_date: date | None = None,
) -> SalesInvoice:
    job = await get_service_job(
        session,
        job_id,
    )

    if job.status not in {
        ServiceJobStatus.READY.value,
        ServiceJobStatus.DELIVERED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service invoice can only be created "
                "for a ready or delivered job"
            ),
        )

    if job.related_invoice_id is not None:
        existing = await session.get(
            SalesInvoice,
            job.related_invoice_id,
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This service job already has "
                    f"invoice {existing.invoice_number}"
                ),
            )

    duplicate_result = await session.execute(
        select(SalesInvoice)
        .where(
            SalesInvoice.source_type
            == InvoiceSourceType.SERVICE_JOB.value,
            SalesInvoice.source_id == job.id,
        )
        .order_by(SalesInvoice.id)
    )

    duplicate = (
        duplicate_result.scalars().first()
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This service job already has "
                f"invoice {duplicate.invoice_number}"
            ),
        )

    customer = await get_customer(
        session,
        job.customer_id,
    )

    branch = await get_branch(
        session,
        job.branch_id,
    )

    if customer.company_id != job.company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service job customer belongs "
                "to another company"
            ),
        )

    if branch.company_id != job.company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service job branch belongs "
                "to another company"
            ),
        )

    parts_total = money(
        sum(
            (
                Decimal(part.line_total)
                for part in job.parts
            ),
            ZERO_2,
        )
    )

    labour_total = (
        ZERO_2
        if job.is_warranty_job
        else money(
            sum(
                (
                    Decimal(labour.amount)
                    for labour in job.labour_items
                ),
                ZERO_2,
            )
        )
    )

    subtotal = money(
        parts_total + labour_total
    )

    discount_amount = money(
        job.discount_amount
    )

    if discount_amount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service job discount exceeds "
                "parts and labour subtotal"
            ),
        )

    grand_total = money(
        subtotal - discount_amount
    )

    if grand_total != money(
        job.final_amount
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service job totals are inconsistent. "
                "Recalculate the service job before "
                "creating the invoice."
            ),
        )

    if subtotal <= ZERO_2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Service job has no billable parts "
                "or labour"
            ),
        )

    invoice = SalesInvoice(
        company_id=job.company_id,
        branch_id=job.branch_id,
        invoice_number=None,
        customer_id=job.customer_id,
        source_type=(
            InvoiceSourceType.SERVICE_JOB.value
        ),
        source_id=job.id,
        subtotal=subtotal,
        discount_amount=discount_amount,
        tax_amount=ZERO_2,
        grand_total=grand_total,
        paid_amount=ZERO_2,
        balance_amount=grand_total,
        due_date=due_date,
        payment_status=(
            PaymentStatus.UNPAID.value
        ),
        invoice_status=(
            InvoiceStatus.DRAFT.value
        ),
        notes=(
            f"Service invoice for "
            f"{job.job_number}"
        ),
        created_by_id=current_user.id,
    )

    session.add(invoice)

    try:
        await session.flush()

        invoice.invoice_number = (
            f"INV-{invoice.id:06d}"
        )

        for part in job.parts:
            product = await session.get(
                Product,
                part.product_id,
            )

            description = (
                product.name
                if product is not None
                else (
                    f"Service part "
                    f"#{part.product_id}"
                )
            )

            session.add(
                SalesInvoiceItem(
                    invoice_id=invoice.id,
                    product_id=part.product_id,
                    item_type=(
                        InvoiceItemType
                        .SERVICE_PART.value
                    ),
                    serial_number_id=None,
                    description=description,
                    quantity=part.quantity,
                    unit_price=part.unit_price,
                    discount_amount=ZERO_2,
                    line_total=part.line_total,
                )
            )

        for labour in (
            []
            if job.is_warranty_job
            else job.labour_items
        ):
            description = labour.description

            if (
                labour.hours is not None
                and Decimal(labour.hours) > ZERO_2
            ):
                description = (
                    f"{description} "
                    f"({labour.hours} hours)"
                )

            session.add(
                SalesInvoiceItem(
                    invoice_id=invoice.id,
                    product_id=None,
                    item_type=(
                        InvoiceItemType.LABOUR.value
                    ),
                    serial_number_id=None,
                    description=description,
                    quantity=ONE_3,
                    unit_price=labour.amount,
                    discount_amount=ZERO_2,
                    line_total=labour.amount,
                )
            )

        await session.flush()

        job.related_invoice_id = invoice.id
        job.updated_by_id = current_user.id

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="sales.service_invoice_created",
            module="sales",
            entity_type="sales_invoice",
            entity_id=invoice.id,
            entity_reference=(
                invoice.invoice_number
            ),
            description=(
                f"Service invoice "
                f"{invoice.invoice_number} "
                "created"
            ),
            before_data=None,
            after_data={
                "invoice":
                    sales_invoice_audit_snapshot(
                        invoice
                    ),
            },
            metadata={
                "service_job_id":
                    job.id,
                "service_job_number":
                    job.job_number,
                "customer_id":
                    invoice.customer_id,
                "branch_id":
                    invoice.branch_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_invoice(
        session,
        invoice.id,
    )


async def confirm_invoice(
    session: AsyncSession,
    invoice_id: int,
    payload: SalesInvoiceConfirmRequest,
    current_user: User,
) -> SalesInvoice:
    invoice = await get_invoice(
        session,
        invoice_id,
    )

    if invoice.invoice_status != (
        InvoiceStatus.DRAFT.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only a draft invoice can "
                "be confirmed"
            ),
        )

    customer = await get_customer(
        session,
        invoice.customer_id,
    )

    invoice_before_snapshot = (
        sales_invoice_audit_snapshot(
            invoice
        )
    )

    customer_before_snapshot = (
        sales_customer_audit_snapshot(
            customer
        )
    )

    now = datetime.now(
        timezone.utc
    )

    try:
        for item in invoice.items:
            item_type = (
                item.item_type
                or InvoiceItemType.PRODUCT.value
            )

            if item_type in {
                InvoiceItemType.SERVICE_PART.value,
                InvoiceItemType.LABOUR.value,
            }:
                continue

            if item_type != (
                InvoiceItemType.PRODUCT.value
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Invoice contains an unsupported "
                        f"item type: {item_type}"
                    ),
                )

            if item.product_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Product invoice item is missing "
                        "its product reference"
                    ),
                )

            product = await session.get(
                Product,
                item.product_id,
            )

            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Invoice contains an invalid product"
                    ),
                )

            if product.track_serial_numbers:
                serial_record = await session.get(
                    ProductSerialNumber,
                    item.serial_number_id,
                )

                if serial_record is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Invoice serial number "
                            "was not found"
                        ),
                    )

                if (
                    serial_record.product_id
                    != product.id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Selected serial number does "
                            "not belong to invoice product"
                        ),
                    )

                if serial_record.status != (
                    SerialNumberStatus.AVAILABLE.value
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Serial "
                            f"{serial_record.serial_number} "
                            "is no longer available"
                        ),
                    )

                if (
                    serial_record.warehouse_id
                    is None
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Selected serial is not "
                            "inside a warehouse"
                        ),
                    )

                warehouse = await session.get(
                    Warehouse,
                    serial_record.warehouse_id,
                )

                if warehouse is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Serial warehouse was not found"
                        ),
                    )

                stock_result = await session.execute(
                    select(StockItem)
                    .where(
                        StockItem.warehouse_id
                        == warehouse.id,
                        StockItem.product_id
                        == product.id,
                    )
                )

                stock_item = (
                    stock_result.scalar_one_or_none()
                )

                if stock_item is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Stock balance does not exist "
                            "for serialized product"
                        ),
                    )

                available = (
                    Decimal(
                        stock_item.quantity_on_hand
                    )
                    - Decimal(
                        stock_item.quantity_reserved
                    )
                )

                if available < ONE_3:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Insufficient stock for "
                            f"{product.product_code}"
                        ),
                    )

                average_cost = money(
                    stock_item.average_cost
                )

                if (
                    average_cost > ZERO_2
                    and money(item.unit_price)
                    < average_cost
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"{product.product_code}: "
                            "sale price "
                            f"{money(item.unit_price):.2f} "
                            "is below stock average cost "
                            f"{average_cost:.2f}"
                        ),
                    )

                stock_item.quantity_on_hand = (
                    Decimal(
                        stock_item.quantity_on_hand
                    )
                    - ONE_3
                )

                original_warehouse_id = (
                    warehouse.id
                )

                serial_record.status = (
                    SerialNumberStatus.SOLD.value
                )

                serial_record.current_customer_id = (
                    customer.id
                )

                serial_record.sold_at = now

                serial_record.warranty_start_date = (
                    now.date()
                )

                if product.warranty_months > 0:
                    serial_record.warranty_end_date = (
                        add_months(
                            now.date(),
                            product.warranty_months,
                        )
                    )

                serial_record.warehouse_id = None

                session.add(
                    StockMovement(
                        company_id=invoice.company_id,
                        branch_id=invoice.branch_id,
                        warehouse_id=(
                            original_warehouse_id
                        ),
                        product_id=product.id,
                        serial_number_id=(
                            serial_record.id
                        ),
                        movement_type=(
                            StockMovementType
                            .SALE_ISSUE.value
                        ),
                        quantity=-ONE_3,
                        unit_cost=(
                            stock_item.average_cost
                        ),
                        reference_type=(
                            "sales_invoice"
                        ),
                        reference_id=(
                            invoice.invoice_number
                        ),
                        notes=(
                            "Automatic stock issue "
                            "from confirmed invoice"
                        ),
                        created_by_id=current_user.id,
                    )
                )

            else:
                if item.warehouse_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"{product.product_code}: "
                            "invoice item has no warehouse"
                        ),
                    )

                warehouse = await session.get(
                    Warehouse,
                    item.warehouse_id,
                )

                if (
                    warehouse is None
                    or warehouse.branch_id
                    != invoice.branch_id
                    or not warehouse.is_active
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"{product.product_code}: "
                            "selected warehouse is invalid "
                            "or inactive"
                        ),
                    )

                warehouse_id = warehouse.id

                stock_result = await session.execute(
                    select(StockItem)
                    .where(
                        StockItem.warehouse_id
                        == warehouse_id,
                        StockItem.product_id
                        == product.id,
                    )
                )

                stock_item = (
                    stock_result.scalar_one_or_none()
                )

                if stock_item is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"No stock balance for "
                            f"{product.product_code}"
                        ),
                    )

                available = (
                    Decimal(
                        stock_item.quantity_on_hand
                    )
                    - Decimal(
                        stock_item.quantity_reserved
                    )
                )

                if item.quantity > available:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Insufficient stock for "
                            f"{product.product_code}. "
                            f"Available: {available}"
                        ),
                    )

                average_cost = money(
                    stock_item.average_cost
                )

                if (
                    average_cost > ZERO_2
                    and money(item.unit_price)
                    < average_cost
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"{product.product_code}: "
                            "sale price "
                            f"{money(item.unit_price):.2f} "
                            "is below stock average cost "
                            f"{average_cost:.2f}"
                        ),
                    )

                stock_item.quantity_on_hand = (
                    Decimal(
                        stock_item.quantity_on_hand
                    )
                    - item.quantity
                )

                session.add(
                    StockMovement(
                        company_id=invoice.company_id,
                        branch_id=invoice.branch_id,
                        warehouse_id=warehouse_id,
                        product_id=product.id,
                        serial_number_id=None,
                        movement_type=(
                            StockMovementType
                            .SALE_ISSUE.value
                        ),
                        quantity=-item.quantity,
                        unit_cost=(
                            stock_item.average_cost
                        ),
                        reference_type=(
                            "sales_invoice"
                        ),
                        reference_id=(
                            invoice.invoice_number
                        ),
                        notes=(
                            "Automatic stock issue "
                            "from confirmed invoice"
                        ),
                        created_by_id=current_user.id,
                    )
                )

        invoice.invoice_status = (
            InvoiceStatus.CONFIRMED.value
        )

        invoice.updated_by_id = (
            current_user.id
        )

        created_initial_payment = None

        initial_payment = (
            payload.initial_payment
        )

        if initial_payment is not None:
            if (
                initial_payment.amount
                > invoice.balance_amount
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_CONTENT
                    ),
                    detail=(
                        "Initial payment cannot exceed "
                        "customer payable balance"
                    ),
                )

            payment = CustomerPayment(
                company_id=invoice.company_id,
                branch_id=invoice.branch_id,
                receipt_number=None,
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                amount=initial_payment.amount,
                payment_method=(
                    initial_payment
                    .payment_method.value
                ),
                reference_number=(
                    initial_payment.reference_number
                ),
                notes=initial_payment.notes,
                created_by_id=current_user.id,
            )

            session.add(payment)

            await session.flush()

            payment.receipt_number = (
                f"REC-{payment.id:06d}"
            )

            created_initial_payment = payment

            invoice.paid_amount = money(
                initial_payment.amount
            )

        invoice.balance_amount = money(
            max(
                ZERO_2,
                Decimal(invoice.grand_total)
                - Decimal(invoice.credited_amount)
                - Decimal(invoice.trade_in_amount)
                - Decimal(invoice.paid_amount),
            )
        )

        if (
            invoice.balance_amount
            == ZERO_2
        ):
            invoice.payment_status = (
                PaymentStatus.PAID.value
            )

        elif invoice.paid_amount > ZERO_2:
            invoice.payment_status = (
                PaymentStatus.PARTIAL.value
            )

        else:
            invoice.payment_status = (
                PaymentStatus.UNPAID.value
            )

        customer.current_balance = money(
            Decimal(
                customer.current_balance
            )
            + invoice.balance_amount
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="sales.invoice_confirmed",
            module="sales",
            entity_type="sales_invoice",
            entity_id=invoice.id,
            entity_reference=(
                invoice.invoice_number
            ),
            description=(
                f"Sales invoice "
                f"{invoice.invoice_number} "
                "confirmed"
            ),
            before_data={
                "invoice":
                    invoice_before_snapshot,
                "customer":
                    customer_before_snapshot,
            },
            after_data={
                "invoice":
                    sales_invoice_audit_snapshot(
                        invoice
                    ),
                "customer":
                    sales_customer_audit_snapshot(
                        customer
                    ),
                "initial_payment": (
                    sales_payment_audit_snapshot(
                        created_initial_payment
                    )
                    if created_initial_payment
                    is not None
                    else None
                ),
            },
            metadata={
                "customer_id":
                    invoice.customer_id,
                "branch_id":
                    invoice.branch_id,
                "source_type":
                    invoice.source_type,
                "source_id":
                    invoice.source_id,
                "initial_payment_created":
                    (
                        created_initial_payment
                        is not None
                    ),
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except Exception:
        await session.rollback()
        raise

    return await get_invoice(
        session,
        invoice.id,
    )


async def post_payment(
    session: AsyncSession,
    payload: PaymentCreate,
    current_user: User,
) -> CustomerPayment:
    invoice = await get_invoice(
        session,
        payload.invoice_id,
    )

    if invoice.invoice_status != (
        InvoiceStatus.CONFIRMED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Payments can only be posted "
                "to confirmed invoices"
            ),
        )

    if invoice.balance_amount <= ZERO_2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invoice has no outstanding balance"
            ),
        )

    if (
        payload.amount
        > invoice.balance_amount
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Payment cannot exceed invoice balance"
            ),
        )

    customer = await get_customer(
        session,
        invoice.customer_id,
    )

    payment = CustomerPayment(
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        receipt_number=None,
        customer_id=invoice.customer_id,
        invoice_id=invoice.id,
        amount=payload.amount,
        payment_method=(
            payload.payment_method.value
        ),
        reference_number=(
            payload.reference_number
        ),
        notes=payload.notes,
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
                ZERO_2,
                Decimal(invoice.grand_total)
                - Decimal(invoice.credited_amount)
                - Decimal(invoice.trade_in_amount)
                - Decimal(invoice.paid_amount),
            )
        )

        invoice.payment_status = (
            PaymentStatus.PAID.value
            if invoice.balance_amount
            == ZERO_2
            else PaymentStatus.PARTIAL.value
        )

        customer.current_balance = money(
            max(
                ZERO_2,
                Decimal(
                    customer.current_balance
                )
                - payload.amount,
            )
        )

        await session.commit()
        await session.refresh(payment)

    except Exception:
        await session.rollback()
        raise

    return payment


async def invoice_detail_response(
    session: AsyncSession,
    invoice: SalesInvoice,
) -> SalesInvoiceDetailResponse:
    customer = await session.get(
        Customer,
        invoice.customer_id,
    )

    return SalesInvoiceDetailResponse(
        id=invoice.id,
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        invoice_number=invoice.invoice_number,
        customer_id=invoice.customer_id,
        source_type=invoice.source_type,
        source_id=invoice.source_id,
        invoice_date=invoice.invoice_date,
        subtotal=invoice.subtotal,
        discount_amount=(
            invoice.discount_amount
        ),
        tax_amount=invoice.tax_amount,
        grand_total=invoice.grand_total,
        credited_amount=invoice.credited_amount,
        trade_in_amount=invoice.trade_in_amount,
        paid_amount=invoice.paid_amount,
        balance_amount=invoice.balance_amount,
        payment_status=(
            invoice.payment_status
        ),
        due_date=invoice.due_date,
        invoice_status=(
            invoice.invoice_status
        ),
        notes=invoice.notes,
        created_by_id=(
            invoice.created_by_id
        ),
        updated_by_id=(
            invoice.updated_by_id
        ),
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        items=invoice.items,
        trade_ins=invoice.trade_ins,
        customer_name=customer.full_name,
        customer_phone=(
            customer.primary_phone
        ),
        payments=invoice.payments,
    )


async def list_invoices(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    invoice_status: str | None,
    payment_status: str | None,
) -> SalesInvoiceListResponse:
    filters = []

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                SalesInvoice
                .invoice_number.ilike(
                    pattern
                ),
                Customer.full_name.ilike(
                    pattern
                ),
                Customer.primary_phone.ilike(
                    pattern
                ),
            )
        )

    if invoice_status is not None:
        filters.append(
            SalesInvoice.invoice_status
            == invoice_status
        )

    if payment_status is not None:
        filters.append(
            SalesInvoice.payment_status
            == payment_status
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(SalesInvoice)
            .join(
                Customer,
                Customer.id
                == SalesInvoice.customer_id,
            )
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(SalesInvoice)
        .join(
            Customer,
            Customer.id
            == SalesInvoice.customer_id,
        )
        .options(
            selectinload(
                SalesInvoice.items
            ),
            selectinload(
                SalesInvoice.trade_ins
            ),
        )
        .where(*filters)
        .order_by(
            SalesInvoice
            .invoice_date.desc(),
            SalesInvoice.id.desc(),
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    invoices = (
        result.scalars().all()
    )

    return SalesInvoiceListResponse(
        items=[
            SalesInvoiceResponse.model_validate(
                invoice
            )
            for invoice in invoices
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
