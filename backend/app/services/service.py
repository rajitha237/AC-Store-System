from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Branch,
    Company,
    Customer,
    Product,
    ProductSerialNumber,
    SalesInvoice,
    ServiceJobCard,
    ServiceJobPart,
    ServiceJobStatus,
    ServiceJobStatusHistory,
    ServiceLabourItem,
    StockItem,
    StockMovement,
    User,
    Warehouse,
)
from app.models.customer import CustomerStatus
from app.models.service import ApprovalStatus
from app.services.sms import queue_customer_service_status_notification
from app.schemas.service import (
    ServiceApprovalRequest,
    ServiceJobCreate,
    ServiceJobDetailResponse,
    ServiceJobListResponse,
    ServiceJobStatusHistoryResponse,
    ServiceJobUpdate,
    ServiceLabourCreate,
    ServiceLabourResponse,
    ServicePartCreate,
    ServicePartResponse,
    ServiceStatusChangeRequest,
)


MONEY_ZERO = Decimal("0.00")
QUANTITY_ZERO = Decimal("0.000")

MONEY_QUANTIZER = Decimal("0.01")
QUANTITY_QUANTIZER = Decimal("0.001")


VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ServiceJobStatus.RECEIVED.value: {
        ServiceJobStatus.INSPECTION.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.INSPECTION.value: {
        ServiceJobStatus.WAITING_APPROVAL.value,
        ServiceJobStatus.APPROVED.value,
        ServiceJobStatus.REPAIRING.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.WAITING_APPROVAL.value: {
        ServiceJobStatus.APPROVED.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.APPROVED.value: {
        ServiceJobStatus.REPAIRING.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.REPAIRING.value: {
        ServiceJobStatus.TESTING.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.TESTING.value: {
        ServiceJobStatus.REPAIRING.value,
        ServiceJobStatus.READY.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.READY.value: {
        ServiceJobStatus.DELIVERED.value,
        ServiceJobStatus.REPAIRING.value,
        ServiceJobStatus.CANCELLED.value,
    },
    ServiceJobStatus.DELIVERED.value: set(),
    ServiceJobStatus.CANCELLED.value: set(),
}


STOCK_CONSUMPTION_ALLOWED_STATUSES = {
    ServiceJobStatus.APPROVED.value,
    ServiceJobStatus.REPAIRING.value,
    ServiceJobStatus.TESTING.value,
}


LABOUR_ALLOWED_STATUSES = {
    ServiceJobStatus.INSPECTION.value,
    ServiceJobStatus.APPROVED.value,
    ServiceJobStatus.REPAIRING.value,
    ServiceJobStatus.TESTING.value,
}


def money(
    value: Decimal | int | float | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        MONEY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def quantity(
    value: Decimal | int | float | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        QUANTITY_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def calculate_final_amount(
    job: ServiceJobCard,
) -> Decimal:
    gross = (
        Decimal(job.labour_total)
        + Decimal(job.parts_total)
    )

    discount = Decimal(
        job.discount_amount
    )

    return money(
        max(
            MONEY_ZERO,
            gross - discount,
        )
    )


async def get_active_company(
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
            detail=(
                "Active company is not configured"
            ),
        )

    return company


async def get_branch(
    session: AsyncSession,
    *,
    branch_id: int | None,
    company_id: int,
) -> Branch:
    if branch_id is not None:
        branch = await session.get(
            Branch,
            branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch was not found",
            )
    else:
        result = await session.execute(
            select(Branch)
            .where(
                Branch.company_id == company_id,
                Branch.is_main_branch.is_(True),
                Branch.is_active.is_(True),
            )
            .order_by(Branch.id)
        )

        branch = result.scalars().first()

        if branch is None:
            result = await session.execute(
                select(Branch)
                .where(
                    Branch.company_id == company_id,
                    Branch.is_active.is_(True),
                )
                .order_by(Branch.id)
            )

            branch = result.scalars().first()

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Active branch is not configured"
            ),
        )

    if branch.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected branch belongs to another company"
            ),
        )

    if not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected branch is inactive",
        )

    return branch


async def get_active_customer(
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

    if customer.status != CustomerStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected customer is not active"
            ),
        )

    return customer


async def get_active_user(
    session: AsyncSession,
    user_id: int,
    *,
    label: str,
) -> User:
    user = await session.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} was not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{label} is inactive",
        )

    return user


async def get_product(
    session: AsyncSession,
    product_id: int,
    *,
    company_id: int,
) -> Product:
    result = await session.execute(
        select(Product)
        .options(
            selectinload(Product.brand)
        )
        .where(
            Product.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product was not found",
        )

    if product.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected product belongs to another company"
            ),
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected product is inactive",
        )

    return product


async def get_serial(
    session: AsyncSession,
    serial_id: int,
    *,
    company_id: int,
) -> ProductSerialNumber:
    serial = await session.get(
        ProductSerialNumber,
        serial_id,
    )

    if serial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Product serial number was not found"
            ),
        )

    if serial.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected serial number belongs "
                "to another company"
            ),
        )

    return serial


async def get_related_invoice(
    session: AsyncSession,
    invoice_id: int,
    *,
    company_id: int,
    customer_id: int,
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

    if invoice.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected invoice belongs to another company"
            ),
        )

    if invoice.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected invoice does not belong "
                "to this customer"
            ),
        )

    return invoice


async def get_warehouse(
    session: AsyncSession,
    warehouse_id: int,
    *,
    branch_id: int,
) -> Warehouse:
    warehouse = await session.get(
        Warehouse,
        warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse was not found",
        )

    if warehouse.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected warehouse does not belong "
                "to the service job branch"
            ),
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected warehouse is inactive",
        )

    return warehouse


async def get_stock_item(
    session: AsyncSession,
    *,
    warehouse_id: int,
    product_id: int,
) -> StockItem:
    result = await session.execute(
        select(StockItem)
        .where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id == product_id,
        )
    )

    stock_item = result.scalar_one_or_none()

    if stock_item is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product does not have a stock "
                "record in the selected warehouse"
            ),
        )

    return stock_item


def is_serial_under_warranty(
    serial: ProductSerialNumber,
) -> bool:
    today = datetime.now(
        timezone.utc
    ).date()

    if serial.warranty_start_date is None:
        return False

    if serial.warranty_end_date is None:
        return False

    return (
        serial.warranty_start_date
        <= today
        <= serial.warranty_end_date
    )


async def create_job_card(
    session: AsyncSession,
    payload: ServiceJobCreate,
    current_user: User,
) -> ServiceJobCard:
    company = await get_active_company(
        session
    )

    branch = await get_branch(
        session,
        branch_id=payload.branch_id,
        company_id=company.id,
    )

    customer = await get_active_customer(
        session,
        payload.customer_id,
    )

    if customer.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Customer belongs to another company"
            ),
        )

    product = None

    if payload.product_id is not None:
        product = await get_product(
            session,
            payload.product_id,
            company_id=company.id,
        )

    serial = None

    if payload.sold_serial_id is not None:
        serial = await get_serial(
            session,
            payload.sold_serial_id,
            company_id=company.id,
        )

        if (
            product is not None
            and serial.product_id != product.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Selected serial number does not "
                    "belong to selected product"
                ),
            )

        if (
            serial.current_customer_id is not None
            and serial.current_customer_id
            != customer.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Selected serial number belongs "
                    "to another customer"
                ),
            )

        if product is None:
            product = await get_product(
                session,
                serial.product_id,
                company_id=company.id,
            )

    related_invoice = None

    if payload.related_invoice_id is not None:
        related_invoice = (
            await get_related_invoice(
                session,
                payload.related_invoice_id,
                company_id=company.id,
                customer_id=customer.id,
            )
        )

    if payload.technician_id is not None:
        await get_active_user(
            session,
            payload.technician_id,
            label="Technician",
        )

    receiving_officer_id = (
        payload.receiving_officer_id
        or current_user.id
    )

    await get_active_user(
        session,
        receiving_officer_id,
        label="Receiving officer",
    )

    warranty_verified = False
    warranty_notes = None

    if payload.is_warranty_job:
        if serial is not None:
            warranty_verified = (
                is_serial_under_warranty(
                    serial
                )
            )

            if warranty_verified:
                warranty_notes = (
                    "Warranty automatically verified "
                    "from sold serial warranty dates."
                )
            else:
                warranty_notes = (
                    "Warranty job created, but the "
                    "serial warranty period could not "
                    "be automatically verified."
                )

        elif related_invoice is not None:
            warranty_notes = (
                "Warranty job linked to sales invoice. "
                "Manual warranty verification required."
            )
        else:
            warranty_notes = (
                "Warranty job created without sold "
                "serial or invoice reference. Manual "
                "verification required."
            )

    serial_number = payload.serial_number
    secondary_serial_number = (
        payload.secondary_serial_number
    )

    if serial is not None:
        serial_number = (
            serial_number
            or serial.serial_number
        )

        secondary_serial_number = (
            secondary_serial_number
            or serial.secondary_serial_number
        )

    brand_name = payload.brand_name
    model_number = payload.model_number

    if product is not None:
        model_number = (
            model_number
            or product.model_number
        )

        if (
            brand_name is None
            and product.brand is not None
        ):
            brand_name = product.brand.name

    job = ServiceJobCard(
        company_id=company.id,
        branch_id=branch.id,
        job_number=None,
        customer_id=customer.id,
        product_id=(
            product.id
            if product is not None
            else None
        ),
        sold_serial_id=(
            serial.id
            if serial is not None
            else None
        ),
        serial_number=serial_number,
        secondary_serial_number=(
            secondary_serial_number
        ),
        brand_name=brand_name,
        model_number=model_number,
        item_color=payload.item_color,
        service_type=payload.service_type.value,
        priority=payload.priority.value,
        status=ServiceJobStatus.RECEIVED.value,
        approval_status=(
            ApprovalStatus.NOT_REQUIRED.value
        ),
        complaint=payload.complaint,
        reported_issue=payload.reported_issue,
        accessories_received=(
            payload.accessories_received
        ),
        physical_condition=(
            payload.physical_condition
        ),
        special_notes=payload.special_notes,
        technician_id=payload.technician_id,
        receiving_officer_id=(
            receiving_officer_id
        ),
        is_warranty_job=(
            payload.is_warranty_job
        ),
        warranty_verified=(
            warranty_verified
        ),
        warranty_notes=warranty_notes,
        related_invoice_id=(
            related_invoice.id
            if related_invoice is not None
            else None
        ),
        estimated_cost=money(
            payload.estimated_cost
        ),
        labour_total=MONEY_ZERO,
        parts_total=MONEY_ZERO,
        discount_amount=MONEY_ZERO,
        final_amount=MONEY_ZERO,
        expected_completion_date=(
            payload.expected_completion_date
        ),
        scheduled_visit_date=(
            payload.scheduled_visit_date
        ),
        created_by_id=current_user.id,
        updated_by_id=None,
    )

    session.add(job)

    try:
        await session.flush()

        job.job_number = (
            f"JOB-{job.id:06d}"
        )

        history = ServiceJobStatusHistory(
            job_card_id=job.id,
            old_status=None,
            new_status=(
                ServiceJobStatus.RECEIVED.value
            ),
            remarks=(
                "Service job card created"
            ),
            changed_by_id=current_user.id,
        )

        session.add(history)

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


async def get_job_card(
    session: AsyncSession,
    job_id: int,
) -> ServiceJobCard:
    result = await session.execute(
        select(ServiceJobCard)
        .options(
            selectinload(
                ServiceJobCard.status_history
            ),
            selectinload(
                ServiceJobCard.customer
            ),
            selectinload(
                ServiceJobCard.product
            ),
            selectinload(
                ServiceJobCard.technician
            ),
            selectinload(
                ServiceJobCard.receiving_officer
            ),
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
        .execution_options(
            populate_existing=True
        )
    )

    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Service job card was not found"
            ),
        )

    return job


async def recalculate_service_totals(
    session: AsyncSession,
    job: ServiceJobCard,
) -> None:
    parts_total = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    ServiceJobPart.line_total
                ),
                0,
            )
        )
        .where(
            ServiceJobPart.job_card_id
            == job.id
        )
    )

    labour_total = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    ServiceLabourItem.amount
                ),
                0,
            )
        )
        .where(
            ServiceLabourItem.job_card_id
            == job.id
        )
    )

    job.parts_total = money(
        parts_total or MONEY_ZERO
    )

    job.labour_total = money(
        labour_total or MONEY_ZERO
    )

    job.final_amount = (
        calculate_final_amount(job)
    )


async def add_service_part(
    session: AsyncSession,
    job_id: int,
    payload: ServicePartCreate,
    current_user: User,
) -> ServiceJobCard:
    job = await get_job_card(
        session,
        job_id,
    )

    if job.status not in (
        STOCK_CONSUMPTION_ALLOWED_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Parts can only be issued when the "
                "job is approved, repairing or testing"
            ),
        )

    product = await get_product(
        session,
        payload.product_id,
        company_id=job.company_id,
    )

    warehouse = await get_warehouse(
        session,
        payload.warehouse_id,
        branch_id=job.branch_id,
    )

    stock_item = await get_stock_item(
        session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    requested_quantity = quantity(
        payload.quantity
    )

    quantity_on_hand = quantity(
        stock_item.quantity_on_hand
    )

    quantity_reserved = quantity(
        stock_item.quantity_reserved
    )

    available_quantity = quantity(
        quantity_on_hand
        - quantity_reserved
    )

    if requested_quantity > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    "Insufficient available stock "
                    "for service issue"
                ),
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "requested_quantity": str(
                    requested_quantity
                ),
                "quantity_on_hand": str(
                    quantity_on_hand
                ),
                "quantity_reserved": str(
                    quantity_reserved
                ),
                "available_quantity": str(
                    available_quantity
                ),
            },
        )

    unit_cost = money(
        stock_item.average_cost
    )

    unit_price = money(
        payload.unit_price
        if payload.unit_price is not None
        else product.selling_price
    )

    line_total = money(
        requested_quantity
        * unit_price
    )

    stock_movement = StockMovement(
        company_id=job.company_id,
        branch_id=job.branch_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        serial_number_id=None,
        movement_type="service_issue",
        quantity=(
            -requested_quantity
        ),
        unit_cost=unit_cost,
        reference_type="service_job",
        reference_id=job.job_number,
        notes=(
            f"Part issued to service job "
            f"{job.job_number}"
        ),
        created_by_id=current_user.id,
    )

    session.add(stock_movement)

    try:
        await session.flush()

        stock_item.quantity_on_hand = (
            quantity_on_hand
            - requested_quantity
        )

        part = ServiceJobPart(
            job_card_id=job.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=requested_quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
            line_total=line_total,
            stock_movement_id=(
                stock_movement.id
            ),
            notes=payload.notes,
            created_by_id=current_user.id,
        )

        session.add(part)

        await session.flush()

        await recalculate_service_totals(
            session,
            job,
        )

        job.updated_by_id = (
            current_user.id
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


async def add_service_labour(
    session: AsyncSession,
    job_id: int,
    payload: ServiceLabourCreate,
    current_user: User,
) -> ServiceJobCard:
    job = await get_job_card(
        session,
        job_id,
    )

    if job.status not in (
        LABOUR_ALLOWED_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Labour can only be added while "
                "the job is under inspection, "
                "approved, repairing or testing"
            ),
        )

    labour = ServiceLabourItem(
        job_card_id=job.id,
        description=payload.description,
        hours=money(
            payload.hours
        ),
        amount=money(
            payload.amount
        ),
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(labour)

    try:
        await session.flush()

        await recalculate_service_totals(
            session,
            job,
        )

        job.updated_by_id = (
            current_user.id
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


async def update_job_card(
    session: AsyncSession,
    job_id: int,
    payload: ServiceJobUpdate,
    current_user: User,
) -> ServiceJobCard:
    job = await get_job_card(
        session,
        job_id,
    )

    if job.status in {
        ServiceJobStatus.DELIVERED.value,
        ServiceJobStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Delivered or cancelled job cards "
                "cannot be edited"
            ),
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if "technician_id" in update_data:
        technician_id = update_data[
            "technician_id"
        ]

        if technician_id is not None:
            await get_active_user(
                session,
                technician_id,
                label="Technician",
            )

    editable_fields = {
        "technician_id",
        "expected_completion_date",
        "scheduled_visit_date",
        "reported_issue",
        "technician_diagnosis",
        "work_performed",
        "testing_result",
        "accessories_received",
        "physical_condition",
        "special_notes",
        "warranty_notes",
        "estimated_cost",
        "discount_amount",
    }

    for field_name, value in (
        update_data.items()
    ):
        if field_name not in editable_fields:
            continue

        if field_name in {
            "estimated_cost",
            "discount_amount",
        }:
            value = money(value)

        setattr(
            job,
            field_name,
            value,
        )

    if (
        Decimal(job.discount_amount)
        >
        (
            Decimal(job.labour_total)
            + Decimal(job.parts_total)
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Discount cannot exceed service "
                "parts and labour total"
            ),
        )

    job.final_amount = (
        calculate_final_amount(job)
    )

    job.updated_by_id = (
        current_user.id
    )

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


def validate_status_transition(
    old_status: str,
    new_status: str,
) -> None:
    if old_status == new_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Job card is already in "
                f"'{new_status}' status"
            ),
        )

    allowed = VALID_STATUS_TRANSITIONS.get(
        old_status,
        set(),
    )

    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Invalid service status transition: "
                f"{old_status} -> {new_status}"
            ),
        )


async def change_job_status(
    session: AsyncSession,
    job_id: int,
    payload: ServiceStatusChangeRequest,
    current_user: User,
) -> ServiceJobCard:
    job = await get_job_card(
        session,
        job_id,
    )

    old_status = job.status
    new_status = payload.new_status.value

    validate_status_transition(
        old_status,
        new_status,
    )

    if (
        new_status
        == ServiceJobStatus.APPROVED.value
        and job.approval_status
        == ApprovalStatus.REJECTED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A rejected job estimate cannot "
                "be moved to approved status"
            ),
        )

    if (
        new_status
        == ServiceJobStatus.REPAIRING.value
        and job.approval_status
        == ApprovalStatus.PENDING.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Customer approval is still pending"
            ),
        )

    if (
        new_status
        == ServiceJobStatus.READY.value
        and not job.testing_result
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Testing result is required before "
                "marking a job as ready"
            ),
        )

    if (
        new_status
        == ServiceJobStatus.DELIVERED.value
        and job.completed_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Job must be completed before delivery"
            ),
        )

    now = datetime.now(
        timezone.utc
    )

    job.status = new_status
    job.updated_by_id = current_user.id

    if new_status == (
        ServiceJobStatus.WAITING_APPROVAL.value
    ):
        job.approval_status = (
            ApprovalStatus.PENDING.value
        )

    if new_status == (
        ServiceJobStatus.APPROVED.value
    ):
        job.approval_status = (
            ApprovalStatus.APPROVED.value
        )

        if job.approval_at is None:
            job.approval_at = now

    if new_status == (
        ServiceJobStatus.READY.value
    ):
        job.completed_at = now

    if new_status == (
        ServiceJobStatus.DELIVERED.value
    ):
        job.delivered_at = now

    history = ServiceJobStatusHistory(
        job_card_id=job.id,
        old_status=old_status,
        new_status=new_status,
        remarks=payload.remarks,
        changed_by_id=current_user.id,
    )

    session.add(history)

    await queue_customer_service_status_notification(
        session,
        job=job,
        status_value=new_status,
    )

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


async def update_approval(
    session: AsyncSession,
    job_id: int,
    payload: ServiceApprovalRequest,
    current_user: User,
) -> ServiceJobCard:
    job = await get_job_card(
        session,
        job_id,
    )

    if job.status in {
        ServiceJobStatus.DELIVERED.value,
        ServiceJobStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Approval cannot be changed for "
                "a closed job"
            ),
        )

    new_approval = (
        payload.approval_status.value
    )

    if new_approval == (
        ApprovalStatus.NOT_REQUIRED.value
    ):
        job.approval_status = (
            ApprovalStatus.NOT_REQUIRED.value
        )
        job.approval_at = None

    elif new_approval == (
        ApprovalStatus.PENDING.value
    ):
        job.approval_status = (
            ApprovalStatus.PENDING.value
        )
        job.approval_at = None

        if job.status == (
            ServiceJobStatus.INSPECTION.value
        ):
            old_status = job.status
            job.status = (
                ServiceJobStatus
                .WAITING_APPROVAL.value
            )

            session.add(
                ServiceJobStatusHistory(
                    job_card_id=job.id,
                    old_status=old_status,
                    new_status=job.status,
                    remarks=(
                        payload.remarks
                        or "Customer approval requested"
                    ),
                    changed_by_id=current_user.id,
                )
            )

    elif new_approval == (
        ApprovalStatus.APPROVED.value
    ):
        job.approval_status = (
            ApprovalStatus.APPROVED.value
        )
        job.approval_at = datetime.now(
            timezone.utc
        )

        if job.status == (
            ServiceJobStatus
            .WAITING_APPROVAL.value
        ):
            old_status = job.status
            job.status = (
                ServiceJobStatus.APPROVED.value
            )

            session.add(
                ServiceJobStatusHistory(
                    job_card_id=job.id,
                    old_status=old_status,
                    new_status=job.status,
                    remarks=(
                        payload.remarks
                        or "Customer approved estimate"
                    ),
                    changed_by_id=current_user.id,
                )
            )

    elif new_approval == (
        ApprovalStatus.REJECTED.value
    ):
        job.approval_status = (
            ApprovalStatus.REJECTED.value
        )
        job.approval_at = datetime.now(
            timezone.utc
        )

    job.updated_by_id = current_user.id

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_job_card(
        session,
        job.id,
    )


async def build_job_detail(
    job: ServiceJobCard,
) -> ServiceJobDetailResponse:
    return ServiceJobDetailResponse(
        id=job.id,
        company_id=job.company_id,
        branch_id=job.branch_id,
        job_number=job.job_number,
        customer_id=job.customer_id,
        product_id=job.product_id,
        sold_serial_id=job.sold_serial_id,
        serial_number=job.serial_number,
        secondary_serial_number=(
            job.secondary_serial_number
        ),
        brand_name=job.brand_name,
        model_number=job.model_number,
        item_color=job.item_color,
        service_type=job.service_type,
        priority=job.priority,
        status=job.status,
        approval_status=(
            job.approval_status
        ),
        complaint=job.complaint,
        reported_issue=job.reported_issue,
        technician_diagnosis=(
            job.technician_diagnosis
        ),
        work_performed=job.work_performed,
        testing_result=job.testing_result,
        accessories_received=(
            job.accessories_received
        ),
        physical_condition=(
            job.physical_condition
        ),
        special_notes=job.special_notes,
        technician_id=job.technician_id,
        receiving_officer_id=(
            job.receiving_officer_id
        ),
        is_warranty_job=(
            job.is_warranty_job
        ),
        warranty_verified=(
            job.warranty_verified
        ),
        warranty_notes=job.warranty_notes,
        related_invoice_id=(
            job.related_invoice_id
        ),
        estimated_cost=job.estimated_cost,
        labour_total=job.labour_total,
        parts_total=job.parts_total,
        discount_amount=(
            job.discount_amount
        ),
        final_amount=job.final_amount,
        received_at=job.received_at,
        expected_completion_date=(
            job.expected_completion_date
        ),
        scheduled_visit_date=(
            job.scheduled_visit_date
        ),
        approval_at=job.approval_at,
        completed_at=job.completed_at,
        delivered_at=job.delivered_at,
        created_by_id=job.created_by_id,
        updated_by_id=job.updated_by_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        customer_name=(
            job.customer.full_name
        ),
        customer_phone=(
            job.customer.primary_phone
        ),
        product_name=(
            job.product.name
            if job.product is not None
            else None
        ),
        product_code=(
            job.product.product_code
            if job.product is not None
            else None
        ),
        technician_name=(
            job.technician.full_name
            if job.technician is not None
            else None
        ),
        receiving_officer_name=(
            job.receiving_officer.full_name
            if job.receiving_officer is not None
            else None
        ),
        status_history=[
            ServiceJobStatusHistoryResponse.model_validate(
                history
            )
            for history in job.status_history
        ],
        parts=[
            ServicePartResponse.model_validate(
                part
            )
            for part in job.parts
        ],
        labour_items=[
            ServiceLabourResponse.model_validate(
                labour
            )
            for labour in job.labour_items
        ],
    )


async def list_job_cards(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    job_status: str | None,
    service_type: str | None,
    priority: str | None,
    technician_id: int | None,
    customer_id: int | None,
    warranty_only: bool,
) -> ServiceJobListResponse:
    filters = []

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                ServiceJobCard.job_number.ilike(
                    pattern
                ),
                ServiceJobCard.serial_number.ilike(
                    pattern
                ),
                ServiceJobCard
                .secondary_serial_number
                .ilike(pattern),
                Customer.full_name.ilike(
                    pattern
                ),
                Customer.primary_phone.ilike(
                    pattern
                ),
            )
        )

    if job_status is not None:
        filters.append(
            ServiceJobCard.status
            == job_status
        )

    if service_type is not None:
        filters.append(
            ServiceJobCard.service_type
            == service_type
        )

    if priority is not None:
        filters.append(
            ServiceJobCard.priority
            == priority
        )

    if technician_id is not None:
        filters.append(
            ServiceJobCard.technician_id
            == technician_id
        )

    if customer_id is not None:
        filters.append(
            ServiceJobCard.customer_id
            == customer_id
        )

    if warranty_only:
        filters.append(
            ServiceJobCard
            .is_warranty_job.is_(True)
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(ServiceJobCard)
            .join(
                Customer,
                Customer.id
                == ServiceJobCard.customer_id,
            )
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(ServiceJobCard)
        .join(
            Customer,
            Customer.id
            == ServiceJobCard.customer_id,
        )
        .options(
            selectinload(
                ServiceJobCard.status_history
            ),
            selectinload(
                ServiceJobCard.customer
            ),
            selectinload(
                ServiceJobCard.product
            ),
            selectinload(
                ServiceJobCard.technician
            ),
            selectinload(
                ServiceJobCard.receiving_officer
            ),
            selectinload(
                ServiceJobCard.parts
            ),
            selectinload(
                ServiceJobCard.labour_items
            ),
        )
        .where(*filters)
        .order_by(
            ServiceJobCard.received_at.desc(),
            ServiceJobCard.id.desc(),
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    jobs = result.scalars().unique().all()

    return ServiceJobListResponse(
        items=[
            await build_job_detail(job)
            for job in jobs
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



# ===== LEGACY SERVICE JOB HISTORY SERVICE =====

async def list_legacy_service_jobs(
    session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    cancelled: bool | None = None,
):
    from math import ceil

    from sqlalchemy import (
        String,
        cast,
        func,
        or_,
        select,
    )

    from app.models.legacy_service_job import (
        LegacyServiceJob,
    )
    from app.schemas.service import (
        LegacyServiceJobHistoryListResponse,
        LegacyServiceJobListItemResponse,
    )

    filters = []

    if search:
        term = f"%{search.strip()}%"

        filters.append(
            or_(
                cast(
                    LegacyServiceJob.legacy_job_id,
                    String,
                ).ilike(term),
                LegacyServiceJob.invoice_code.ilike(term),
                LegacyServiceJob.reference_no.ilike(term),
                LegacyServiceJob.customer_name.ilike(term),
                LegacyServiceJob.customer_phone.ilike(term),
                LegacyServiceJob.customer_address.ilike(term),
                LegacyServiceJob.legacy_user_name.ilike(term),
            )
        )

    if cancelled is not None:
        filters.append(
            LegacyServiceJob.is_cancelled == cancelled
        )

    count_stmt = (
        select(func.count(LegacyServiceJob.id))
        .where(*filters)
    )

    total = (
        await session.execute(count_stmt)
    ).scalar_one()

    offset = (page - 1) * page_size

    stmt = (
        select(LegacyServiceJob)
        .where(*filters)
        .order_by(
            LegacyServiceJob.job_date.desc(),
            LegacyServiceJob.job_time.desc(),
            LegacyServiceJob.legacy_job_id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    rows = (
        await session.execute(stmt)
    ).scalars().all()

    items = [
        LegacyServiceJobListItemResponse.model_validate(
            row
        )
        for row in rows
    ]

    pages = (
        ceil(total / page_size)
        if total
        else 0
    )

    return LegacyServiceJobHistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def get_legacy_service_job(
    session,
    legacy_job_id: int,
):
    from fastapi import HTTPException
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.legacy_service_job import (
        LegacyServiceJob,
    )
    from app.schemas.service import (
        LegacyServiceJobDetailResponse,
    )

    stmt = (
        select(LegacyServiceJob)
        .options(
            selectinload(
                LegacyServiceJob.lines
            )
        )
        .where(
            LegacyServiceJob.legacy_job_id
            == legacy_job_id
        )
    )

    job = (
        await session.execute(stmt)
    ).scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Legacy service job not found",
        )

    ordered_lines = sorted(
        job.lines,
        key=lambda line: line.line_number,
    )

    return LegacyServiceJobDetailResponse(
        id=job.id,
        legacy_job_id=job.legacy_job_id,
        invoice_code=job.invoice_code,
        job_date=job.job_date,
        job_time=job.job_time,
        reference_no=job.reference_no,
        sale_type=job.sale_type,
        legacy_customer_id=job.legacy_customer_id,
        customer_name=job.customer_name,
        customer_phone=job.customer_phone,
        customer_address=job.customer_address,
        bill_discount=job.bill_discount,
        bill_discount_value=job.bill_discount_value,
        source_total=job.source_total,
        net_amount=job.net_amount,
        gross_amount=job.gross_amount,
        profit=job.profit,
        pay_amount=job.pay_amount,
        rest_amount=job.rest_amount,
        cash_amount=job.cash_amount,
        credit_amount=job.credit_amount,
        cheque_amount=job.cheque_amount,
        card_amount=job.card_amount,
        bank_amount=job.bank_amount,
        over_balance_amount=job.over_balance_amount,
        balance_amount=job.balance_amount,
        is_cancelled=job.is_cancelled,
        legacy_user_id=job.legacy_user_id,
        legacy_user_name=job.legacy_user_name,
        legacy_service_date=job.legacy_service_date,
        legacy_warranty_period=job.legacy_warranty_period,
        management_status=job.management_status,
        status_remarks=job.status_remarks,
        status_updated_at=job.status_updated_at,
        status_updated_by_id=job.status_updated_by_id,
        migration_notes=job.migration_notes,
        lines=ordered_lines,
    )



# ===== LEGACY SERVICE JOB STATUS MANAGEMENT =====

LEGACY_SERVICE_MANAGEMENT_STATUSES = {
    "received",
    "inspection",
    "waiting_approval",
    "approved",
    "repairing",
    "testing",
    "ready",
    "delivered",
    "cancelled",
}


async def update_legacy_service_job_status(
    session,
    *,
    legacy_job_id: int,
    status: str,
    remarks: str | None,
    user_id: int | None,
):
    from datetime import UTC, datetime

    from fastapi import HTTPException
    from sqlalchemy import select

    from app.models.legacy_service_job import (
        LegacyServiceJob,
    )
    from app.schemas.service import (
        LegacyServiceJobStatusUpdateResponse,
    )

    normalized_status = (
        status.strip().lower()
    )

    if (
        normalized_status
        not in LEGACY_SERVICE_MANAGEMENT_STATUSES
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Invalid legacy service management status"
            ),
        )

    stmt = (
        select(LegacyServiceJob)
        .where(
            LegacyServiceJob.legacy_job_id
            == legacy_job_id
        )
    )

    job = (
        await session.execute(stmt)
    ).scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Legacy service job not found",
        )

    cleaned_remarks = (
        remarks.strip()
        if remarks
        else None
    )

    if cleaned_remarks:
        cleaned_remarks = (
            cleaned_remarks[:1000]
        )

    now = datetime.now(UTC)

    job.management_status = (
        normalized_status
    )
    job.status_remarks = (
        cleaned_remarks
    )
    job.status_updated_at = now
    job.status_updated_by_id = user_id

    await session.flush()
    await session.commit()
    await session.refresh(job)

    return LegacyServiceJobStatusUpdateResponse(
        legacy_job_id=job.legacy_job_id,
        management_status=(
            job.management_status
        ),
        status_remarks=job.status_remarks,
        status_updated_at=(
            job.status_updated_at
            or now
        ),
        status_updated_by_id=(
            job.status_updated_by_id
        ),
    )
