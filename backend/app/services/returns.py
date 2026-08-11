from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Customer,
    Product,
    ProductSerialNumber,
    SalesInvoice,
    SalesInvoiceItem,
    StockItem,
    StockMovement,
    User,
    Warehouse,
)
from app.models.inventory import (
    SerialNumberStatus,
    StockMovementType,
    WarehouseType,
)
from app.models.returns import (
    ReturnItemCondition,
    ReturnResolution,
    ReturnStatus,
    SalesReturn,
    SalesReturnItem,
    SalesReturnStatusHistory,
)
from app.models.sales import (
    InvoiceItemType,
    InvoiceStatus,
)
from app.services.audit import create_audit_log
from app.schemas.returns import (
    ReplacementItemRequest,
    ReturnApprovalRequest,
    ReturnInspectionRequest,
    ReturnStatusChangeRequest,
    SalesReturnCreate,
    SalesReturnDetailResponse,
    SalesReturnListResponse,
)
from app.services.inventory import (
    add_months,
    calculate_weighted_average_cost,
    get_or_create_stock_item,
)


ZERO_2 = Decimal("0.00")
ZERO_3 = Decimal("0.000")
ONE_3 = Decimal("1.000")


def money(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


def qty(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.001")
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



def sales_return_audit_snapshot(
    sales_return: SalesReturn,
) -> dict:
    return {
        "id":
            sales_return.id,
        "return_number":
            sales_return.return_number,
        "company_id":
            sales_return.company_id,
        "branch_id":
            sales_return.branch_id,
        "invoice_id":
            sales_return.invoice_id,
        "customer_id":
            sales_return.customer_id,
        "return_type":
            sales_return.return_type,
        "status":
            sales_return.status,
        "resolution":
            sales_return.resolution,
        "reason":
            sales_return.reason,
        "inspection_notes":
            sales_return.inspection_notes,
        "approval_notes":
            sales_return.approval_notes,
        "subtotal":
            str(money(sales_return.subtotal)),
        "refund_amount":
            str(money(
                sales_return.refund_amount
            )),
        "approved_by_id":
            sales_return.approved_by_id,
        "approved_at":
            sales_return.approved_at,
        "completed_at":
            sales_return.completed_at,
        "created_by_id":
            sales_return.created_by_id,
        "updated_by_id":
            sales_return.updated_by_id,
    }


async def get_return(
    session: AsyncSession,
    return_id: int,
) -> SalesReturn:
    result = await session.execute(
        select(SalesReturn)
        .options(
            selectinload(SalesReturn.items),
            selectinload(
                SalesReturn.status_history
            ),
        )
        .where(
            SalesReturn.id == return_id
        )
        .execution_options(
            populate_existing=True
        )
    )

    sales_return = (
        result.scalar_one_or_none()
    )

    if sales_return is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales return was not found",
        )

    return sales_return


async def get_invoice(
    session: AsyncSession,
    invoice_id: int,
) -> SalesInvoice:
    result = await session.execute(
        select(SalesInvoice)
        .options(
            selectinload(SalesInvoice.items)
        )
        .where(
            SalesInvoice.id == invoice_id
        )
    )

    invoice = result.scalar_one_or_none()

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice was not found",
        )

    return invoice


async def add_status_history(
    session: AsyncSession,
    *,
    sales_return: SalesReturn,
    old_status: str | None,
    new_status: str,
    current_user: User,
    remarks: str | None = None,
) -> None:
    session.add(
        SalesReturnStatusHistory(
            return_id=sales_return.id,
            old_status=old_status,
            new_status=new_status,
            remarks=remarks,
            changed_by_id=current_user.id,
        )
    )


async def returned_quantity_for_item(
    session: AsyncSession,
    invoice_item_id: int,
) -> Decimal:
    value = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    SalesReturnItem.quantity
                ),
                ZERO_3,
            )
        )
        .select_from(SalesReturnItem)
        .join(
            SalesReturn,
            SalesReturn.id
            == SalesReturnItem.return_id,
        )
        .where(
            SalesReturnItem.invoice_item_id
            == invoice_item_id,
            SalesReturn.status.notin_(
                [
                    ReturnStatus.REJECTED.value,
                    ReturnStatus.CANCELLED.value,
                ]
            ),
        )
    )

    return qty(
        value or ZERO_3
    )


async def validate_destination_warehouse(
    session: AsyncSession,
    *,
    warehouse_id: int,
    branch_id: int,
    condition: str,
) -> Warehouse:
    warehouse = await session.get(
        Warehouse,
        warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Destination warehouse was not found"
            ),
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Destination warehouse is inactive"
            ),
        )

    if warehouse.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Destination warehouse belongs "
                "to another branch"
            ),
        )

    if condition in {
        ReturnItemCondition.FAULTY.value,
        ReturnItemCondition.DAMAGED.value,
    }:
        allowed_types = {
            WarehouseType.FAULTY.value,
            WarehouseType.RETURNED.value,
        }
    else:
        allowed_types = {
            WarehouseType.RETURNED.value,
        }

    if (
        warehouse.warehouse_type
        not in allowed_types
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected warehouse type is not "
                "valid for this return condition"
            ),
        )

    return warehouse


async def find_default_return_warehouse(
    session: AsyncSession,
    *,
    branch_id: int,
    condition: str,
) -> Warehouse:
    preferred_type = (
        WarehouseType.FAULTY.value
        if condition in {
            ReturnItemCondition.FAULTY.value,
            ReturnItemCondition.DAMAGED.value,
        }
        else WarehouseType.RETURNED.value
    )

    result = await session.execute(
        select(Warehouse)
        .where(
            Warehouse.branch_id == branch_id,
            Warehouse.warehouse_type
            == preferred_type,
            Warehouse.is_active.is_(True),
        )
        .order_by(Warehouse.id)
    )

    warehouse = result.scalars().first()

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"No active {preferred_type} "
                "warehouse is configured"
            ),
        )

    return warehouse


async def original_sale_unit_cost(
    session: AsyncSession,
    *,
    invoice: SalesInvoice,
    item: SalesReturnItem,
    product: Product,
) -> Decimal:
    filters = [
        StockMovement.reference_type
        == "sales_invoice",
        StockMovement.reference_id
        == invoice.invoice_number,
        StockMovement.product_id
        == product.id,
        StockMovement.movement_type
        == StockMovementType.SALE_ISSUE.value,
    ]

    if item.serial_number_id is not None:
        filters.append(
            StockMovement.serial_number_id
            == item.serial_number_id
        )

    result = await session.execute(
        select(StockMovement.unit_cost)
        .where(*filters)
        .order_by(
            StockMovement.id.desc()
        )
    )

    unit_cost = result.scalars().first()

    if unit_cost is not None:
        return money(unit_cost)

    return money(
        product.purchase_cost
    )


async def create_return(
    session: AsyncSession,
    payload: SalesReturnCreate,
    current_user: User,
) -> SalesReturn:
    invoice = await get_invoice(
        session,
        payload.invoice_id,
    )

    if invoice.invoice_status not in {
        InvoiceStatus.CONFIRMED.value,
        InvoiceStatus.RETURNED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Returns can only be created "
                "for confirmed invoices"
            ),
        )

    customer = await session.get(
        Customer,
        invoice.customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice customer was not found",
        )

    invoice_items = {
        item.id: item
        for item in invoice.items
    }

    prepared_items: list[
        tuple[
            object,
            SalesInvoiceItem,
            Decimal,
            Decimal,
        ]
    ] = []

    subtotal = ZERO_2

    for requested in payload.items:
        invoice_item = invoice_items.get(
            requested.invoice_item_id
        )

        if invoice_item is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    f"Invoice item "
                    f"{requested.invoice_item_id} "
                    "does not belong to this invoice"
                ),
            )

        if (
            invoice_item.product_id is None
            or invoice_item.item_type
            == InvoiceItemType.LABOUR.value
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Labour or non-product invoice "
                    "items cannot be physically returned"
                ),
            )

        product = await session.get(
            Product,
            invoice_item.product_id,
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Product "
                    f"{invoice_item.product_id} "
                    "was not found"
                ),
            )

        requested_qty = qty(
            requested.quantity
        )

        already_returned = (
            await returned_quantity_for_item(
                session,
                invoice_item.id,
            )
        )

        remaining_qty = qty(
            Decimal(invoice_item.quantity)
            - already_returned
        )

        if requested_qty > remaining_qty:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    f"Invoice item "
                    f"{invoice_item.id} has only "
                    f"{remaining_qty} remaining "
                    "returnable quantity"
                ),
            )

        if product.track_serial_numbers:
            if (
                invoice_item.serial_number_id
                is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Serialized invoice item has "
                        "no serial-number reference"
                    ),
                )

            if requested_qty != ONE_3:
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_CONTENT
                    ),
                    detail=(
                        "Serialized return quantity "
                        "must be exactly 1"
                    ),
                )

            serial = await session.get(
                ProductSerialNumber,
                invoice_item.serial_number_id,
            )

            if serial is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Sold serial-number record "
                        "was not found"
                    ),
                )

            if (
                serial.current_customer_id
                not in {
                    None,
                    invoice.customer_id,
                }
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Serial number belongs "
                        "to another customer"
                    ),
                )

        invoice_qty = Decimal(
            invoice_item.quantity
        )

        if invoice_qty <= ZERO_3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Invoice item quantity is invalid"
                ),
            )

        proportional_total = money(
            Decimal(invoice_item.line_total)
            * requested_qty
            / invoice_qty
        )

        subtotal = money(
            subtotal + proportional_total
        )

        prepared_items.append(
            (
                requested,
                invoice_item,
                requested_qty,
                proportional_total,
            )
        )

    sales_return = SalesReturn(
        company_id=invoice.company_id,
        branch_id=invoice.branch_id,
        return_number=None,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        return_type=payload.return_type.value,
        status=ReturnStatus.REQUESTED.value,
        resolution=ReturnResolution.PENDING.value,
        reason=payload.reason,
        inspection_notes=None,
        approval_notes=None,
        subtotal=subtotal,
        refund_amount=ZERO_2,
        approved_by_id=None,
        approved_at=None,
        completed_at=None,
        created_by_id=current_user.id,
        updated_by_id=None,
    )

    session.add(sales_return)

    try:
        await session.flush()

        sales_return.return_number = (
            f"RET-{sales_return.id:06d}"
        )

        for (
            requested,
            invoice_item,
            requested_qty,
            proportional_total,
        ) in prepared_items:
            if (
                requested.destination_warehouse_id
                is not None
            ):
                await validate_destination_warehouse(
                    session,
                    warehouse_id=(
                        requested
                        .destination_warehouse_id
                    ),
                    branch_id=invoice.branch_id,
                    condition=(
                        requested.condition.value
                    ),
                )

            session.add(
                SalesReturnItem(
                    return_id=sales_return.id,
                    invoice_item_id=(
                        invoice_item.id
                    ),
                    product_id=(
                        invoice_item.product_id
                    ),
                    serial_number_id=(
                        invoice_item
                        .serial_number_id
                    ),
                    quantity=requested_qty,
                    unit_price=money(
                        invoice_item.unit_price
                    ),
                    line_total=(
                        proportional_total
                    ),
                    condition=(
                        requested.condition.value
                    ),
                    reason=requested.reason,
                    destination_warehouse_id=(
                        requested
                        .destination_warehouse_id
                    ),
                    stock_movement_id=None,
                    replacement_product_id=None,
                    replacement_serial_number_id=None,
                    replacement_stock_movement_id=None,
                    notes=None,
                )
            )

        await add_status_history(
            session,
            sales_return=sales_return,
            old_status=None,
            new_status=(
                ReturnStatus.REQUESTED.value
            ),
            current_user=current_user,
            remarks="Sales return request created",
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="return.created",
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=(
                f"Sales return "
                f"{sales_return.return_number} "
                "created"
            ),
            before_data=None,
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
            },
            metadata={
                "invoice_id":
                    sales_return.invoice_id,
                "customer_id":
                    sales_return.customer_id,
                "branch_id":
                    sales_return.branch_id,
                "item_count":
                    len(prepared_items),
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        sales_return.id,
    )


async def inspect_return(
    session: AsyncSession,
    return_id: int,
    payload: ReturnInspectionRequest,
    current_user: User,
) -> SalesReturn:
    sales_return = await get_return(
        session,
        return_id,
    )

    if sales_return.status not in {
        ReturnStatus.REQUESTED.value,
        ReturnStatus.INSPECTION.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This return cannot be inspected "
                "in its current status"
            ),
        )

    old_status = sales_return.status

    return_before_snapshot = (
        sales_return_audit_snapshot(
            sales_return
        )
    )

    sales_return.inspection_notes = (
        payload.inspection_notes
    )

    sales_return.status = (
        ReturnStatus.WAITING_APPROVAL.value
    )

    sales_return.updated_by_id = (
        current_user.id
    )

    await add_status_history(
        session,
        sales_return=sales_return,
        old_status=old_status,
        new_status=(
            ReturnStatus.WAITING_APPROVAL.value
        ),
        current_user=current_user,
        remarks=payload.inspection_notes,
    )

    try:
        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="return.inspected",
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=(
                f"Sales return "
                f"{sales_return.return_number} "
                "inspected"
            ),
            before_data={
                "return":
                    return_before_snapshot,
            },
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
            },
            metadata={
                "old_status":
                    old_status,
                "new_status":
                    sales_return.status,
                "invoice_id":
                    sales_return.invoice_id,
                "customer_id":
                    sales_return.customer_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        return_id,
    )


async def approve_return(
    session: AsyncSession,
    return_id: int,
    payload: ReturnApprovalRequest,
    current_user: User,
) -> SalesReturn:
    sales_return = await get_return(
        session,
        return_id,
    )

    if sales_return.status != (
        ReturnStatus.WAITING_APPROVAL.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Return must be waiting for "
                "approval"
            ),
        )

    old_status = sales_return.status

    return_before_snapshot = (
        sales_return_audit_snapshot(
            sales_return
        )
    )

    now = utc_now()

    if payload.approved:
        if (
            payload.refund_amount
            > sales_return.subtotal
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Refund amount cannot exceed "
                    "the return subtotal"
                ),
            )

        if (
            payload.resolution
            == ReturnResolution.REFUND
        ):
            invoice = await get_invoice(
                session,
                sales_return.invoice_id,
            )

            if (
                payload.refund_amount
                > Decimal(invoice.paid_amount)
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_CONTENT
                    ),
                    detail=(
                        "Refund amount cannot exceed "
                        "the amount paid on the invoice"
                    ),
                )

        sales_return.status = (
            ReturnStatus.APPROVED.value
        )

        sales_return.resolution = (
            payload.resolution.value
        )

        sales_return.refund_amount = money(
            payload.refund_amount
        )

        sales_return.approved_by_id = (
            current_user.id
        )

        sales_return.approved_at = now

        new_status = (
            ReturnStatus.APPROVED.value
        )

    else:
        sales_return.status = (
            ReturnStatus.REJECTED.value
        )

        sales_return.resolution = (
            ReturnResolution.REJECTED.value
        )

        sales_return.refund_amount = ZERO_2

        sales_return.approved_by_id = (
            current_user.id
        )

        sales_return.approved_at = now

        new_status = (
            ReturnStatus.REJECTED.value
        )

    sales_return.approval_notes = (
        payload.approval_notes
    )

    sales_return.updated_by_id = (
        current_user.id
    )

    await add_status_history(
        session,
        sales_return=sales_return,
        old_status=old_status,
        new_status=new_status,
        current_user=current_user,
        remarks=payload.approval_notes,
    )

    try:
        audit_action = (
            "return.approved"
            if payload.approved
            else "return.rejected"
        )

        audit_description = (
            f"Sales return "
            f"{sales_return.return_number} "
            + (
                "approved"
                if payload.approved
                else "rejected"
            )
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=audit_action,
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=audit_description,
            before_data={
                "return":
                    return_before_snapshot,
            },
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
            },
            metadata={
                "old_status":
                    old_status,
                "new_status":
                    sales_return.status,
                "resolution":
                    sales_return.resolution,
                "refund_amount":
                    str(money(
                        sales_return.refund_amount
                    )),
                "invoice_id":
                    sales_return.invoice_id,
                "customer_id":
                    sales_return.customer_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        return_id,
    )


async def receive_returned_stock(
    session: AsyncSession,
    sales_return: SalesReturn,
    current_user: User,
) -> None:
    invoice = await get_invoice(
        session,
        sales_return.invoice_id,
    )

    for return_item in sales_return.items:
        if (
            return_item.stock_movement_id
            is not None
        ):
            continue

        if return_item.product_id is None:
            continue

        product = await session.get(
            Product,
            return_item.product_id,
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Returned product "
                    f"{return_item.product_id} "
                    "was not found"
                ),
            )

        if (
            return_item
            .destination_warehouse_id
            is not None
        ):
            warehouse = (
                await validate_destination_warehouse(
                    session,
                    warehouse_id=(
                        return_item
                        .destination_warehouse_id
                    ),
                    branch_id=(
                        sales_return.branch_id
                    ),
                    condition=(
                        return_item.condition
                    ),
                )
            )

        else:
            warehouse = (
                await find_default_return_warehouse(
                    session,
                    branch_id=(
                        sales_return.branch_id
                    ),
                    condition=(
                        return_item.condition
                    ),
                )
            )

            return_item.destination_warehouse_id = (
                warehouse.id
            )

        unit_cost = (
            await original_sale_unit_cost(
                session,
                invoice=invoice,
                item=return_item,
                product=product,
            )
        )

        stock_item = (
            await get_or_create_stock_item(
                session=session,
                warehouse_id=warehouse.id,
                product_id=product.id,
            )
        )

        old_qty = Decimal(
            stock_item.quantity_on_hand
        )

        old_average_cost = Decimal(
            stock_item.average_cost
        )

        returned_qty = qty(
            return_item.quantity
        )

        stock_item.average_cost = (
            calculate_weighted_average_cost(
                old_quantity=old_qty,
                old_average_cost=(
                    old_average_cost
                ),
                received_quantity=(
                    returned_qty
                ),
                received_unit_cost=unit_cost,
            )
        )

        stock_item.quantity_on_hand = qty(
            old_qty + returned_qty
        )

        if product.track_serial_numbers:
            if (
                return_item.serial_number_id
                is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Serialized return item has "
                        "no serial-number reference"
                    ),
                )

            if returned_qty != ONE_3:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Serialized return quantity "
                        "must be exactly 1"
                    ),
                )

            serial = await session.get(
                ProductSerialNumber,
                return_item.serial_number_id,
            )

            if serial is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Returned serial-number "
                        "record was not found"
                    ),
                )

            serial.warehouse_id = warehouse.id
            serial.current_customer_id = None

            if (
                return_item.condition
                == ReturnItemCondition.FAULTY.value
            ):
                serial.status = (
                    SerialNumberStatus.FAULTY.value
                )

            elif (
                return_item.condition
                == ReturnItemCondition.DAMAGED.value
            ):
                serial.status = (
                    SerialNumberStatus.DAMAGED.value
                )

            else:
                serial.status = (
                    SerialNumberStatus
                    .CUSTOMER_RETURNED.value
                )

        movement = StockMovement(
            company_id=(
                sales_return.company_id
            ),
            branch_id=(
                sales_return.branch_id
            ),
            warehouse_id=warehouse.id,
            product_id=product.id,
            serial_number_id=(
                return_item.serial_number_id
            ),
            movement_type=(
                StockMovementType
                .SALE_RETURN.value
            ),
            quantity=returned_qty,
            unit_cost=unit_cost,
            reference_type="sales_return",
            reference_id=(
                sales_return.return_number
            ),
            notes=(
                f"Customer return "
                f"{sales_return.return_number}"
            ),
            created_by_id=current_user.id,
        )

        session.add(movement)
        await session.flush()

        return_item.stock_movement_id = (
            movement.id
        )


async def reverse_returned_stock(
    session: AsyncSession,
    sales_return: SalesReturn,
    current_user: User,
) -> None:
    return_items_result = await session.execute(
        select(SalesReturnItem)
        .where(
            SalesReturnItem.return_id
            == sales_return.id
        )
        .order_by(
            SalesReturnItem.id
        )
    )

    return_items = (
        return_items_result
        .scalars()
        .all()
    )

    for return_item in return_items:
        if return_item.stock_movement_id is None:
            continue

        original_movement = await session.get(
            StockMovement,
            return_item.stock_movement_id,
        )

        if original_movement is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Original return stock movement "
                    "was not found"
                ),
            )

        if original_movement.movement_type != (
            StockMovementType.SALE_RETURN.value
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Referenced stock movement is "
                    "not a sale-return movement"
                ),
            )

        reversal_reference = (
            f"{sales_return.return_number}:"
            f"{original_movement.id}"
        )

        existing_reversal = await session.scalar(
            select(StockMovement.id)
            .where(
                StockMovement.movement_type
                == StockMovementType
                .SALE_RETURN_REVERSAL.value,
                StockMovement.reference_type
                == "sales_return_reversal",
                StockMovement.reference_id
                == reversal_reference,
            )
            .limit(1)
        )

        if existing_reversal is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Returned stock has already "
                    "been reversed"
                ),
            )

        returned_qty = qty(
            original_movement.quantity
        )

        if returned_qty <= ZERO_3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Original sale-return movement "
                    "has an invalid quantity"
                ),
            )

        stock_result = await session.execute(
            select(StockItem)
            .where(
                StockItem.warehouse_id
                == original_movement.warehouse_id,
                StockItem.product_id
                == original_movement.product_id,
            )
        )

        stock_item = (
            stock_result.scalar_one_or_none()
        )

        if stock_item is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Stock balance for returned "
                    "product was not found"
                ),
            )

        current_qty = qty(
            stock_item.quantity_on_hand
        )

        reserved_qty = qty(
            stock_item.quantity_reserved
        )

        remaining_qty = qty(
            current_qty - returned_qty
        )

        if remaining_qty < ZERO_3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Return reversal would create "
                    "negative stock"
                ),
            )

        if remaining_qty < reserved_qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Return reversal would reduce "
                    "stock below reserved quantity"
                ),
            )

        current_average_cost = money(
            stock_item.average_cost
        )

        return_unit_cost = money(
            original_movement.unit_cost
        )

        if remaining_qty == ZERO_3:
            new_average_cost = ZERO_2
        else:
            remaining_value = (
                Decimal(current_qty)
                * Decimal(current_average_cost)
                - Decimal(returned_qty)
                * Decimal(return_unit_cost)
            )

            if remaining_value < ZERO_2:
                # Minor historical rounding differences
                # must never produce negative inventory value.
                remaining_value = ZERO_2

            new_average_cost = money(
                remaining_value
                / Decimal(remaining_qty)
            )

        stock_item.quantity_on_hand = (
            remaining_qty
        )

        stock_item.average_cost = (
            new_average_cost
        )

        if (
            original_movement.serial_number_id
            is not None
        ):
            if returned_qty != ONE_3:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Serialized return reversal "
                        "quantity must be exactly 1"
                    ),
                )

            serial = await session.get(
                ProductSerialNumber,
                original_movement.serial_number_id,
            )

            if serial is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Returned serial-number "
                        "record was not found"
                    ),
                )

            if (
                serial.warehouse_id
                != original_movement.warehouse_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Returned serial number is "
                        "no longer in the original "
                        "return warehouse"
                    ),
                )

            serial.status = (
                SerialNumberStatus.SOLD.value
            )

            serial.current_customer_id = (
                sales_return.customer_id
            )

            serial.warehouse_id = None

        reversal_movement = StockMovement(
            company_id=sales_return.company_id,
            branch_id=sales_return.branch_id,
            warehouse_id=(
                original_movement.warehouse_id
            ),
            product_id=(
                original_movement.product_id
            ),
            serial_number_id=(
                original_movement.serial_number_id
            ),
            movement_type=(
                StockMovementType
                .SALE_RETURN_REVERSAL.value
            ),
            quantity=-returned_qty,
            unit_cost=return_unit_cost,
            reference_type=(
                "sales_return_reversal"
            ),
            reference_id=(
                reversal_reference
            ),
            notes=(
                f"Reversal of customer return "
                f"{sales_return.return_number}; "
                f"original movement "
                f"{original_movement.id}"
            ),
            created_by_id=current_user.id,
        )

        session.add(reversal_movement)

        await session.flush()


async def process_refund(
    session: AsyncSession,
    sales_return: SalesReturn,
    current_user: User,
) -> None:
    del session
    del current_user

    if sales_return.resolution != (
        ReturnResolution.REFUND.value
    ):
        return

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Refund is approved but cannot be "
            "financially posted yet. A dedicated "
            "refund/credit-note transaction ledger "
            "must be created before cash refunds "
            "are processed."
        ),
    )


async def process_return(
    session: AsyncSession,
    return_id: int,
    current_user: User,
) -> SalesReturn:
    sales_return = await get_return(
        session,
        return_id,
    )

    if sales_return.status != (
        ReturnStatus.APPROVED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only approved returns can "
                "be processed"
            ),
        )

    if sales_return.resolution in {
        ReturnResolution.REFUND.value,
        ReturnResolution.STORE_CREDIT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This financial resolution needs "
                "the refund/credit-note ledger "
                "before processing can continue"
            ),
        )

    old_status = sales_return.status

    return_before_snapshot = (
        sales_return_audit_snapshot(
            sales_return
        )
    )

    try:
        await receive_returned_stock(
            session,
            sales_return,
            current_user,
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
            old_status=old_status,
            new_status=(
                ReturnStatus.PROCESSING.value
            ),
            current_user=current_user,
            remarks=(
                "Returned stock received "
                "and processing started"
            ),
        )

        if sales_return.resolution in {
            ReturnResolution
            .WARRANTY_SERVICE.value,
        }:
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
                    ReturnStatus
                    .PROCESSING.value
                ),
                new_status=(
                    ReturnStatus
                    .COMPLETED.value
                ),
                current_user=current_user,
                remarks=(
                    "Warranty return stock "
                    "processing completed"
                ),
            )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="return.processed",
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=(
                f"Sales return "
                f"{sales_return.return_number} "
                "processed"
            ),
            before_data={
                "return":
                    return_before_snapshot,
            },
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
            },
            metadata={
                "old_status":
                    old_status,
                "new_status":
                    sales_return.status,
                "resolution":
                    sales_return.resolution,
                "invoice_id":
                    sales_return.invoice_id,
                "customer_id":
                    sales_return.customer_id,
                "completed":
                    (
                        sales_return.status
                        == ReturnStatus
                        .COMPLETED.value
                    ),
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        return_id,
    )


async def set_replacement_item(
    session: AsyncSession,
    return_id: int,
    payload: ReplacementItemRequest,
    current_user: User,
) -> SalesReturn:
    sales_return = await get_return(
        session,
        return_id,
    )

    if sales_return.resolution != (
        ReturnResolution.REPLACEMENT.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This return is not approved "
                "for replacement"
            ),
        )

    if sales_return.status not in {
        ReturnStatus.APPROVED.value,
        ReturnStatus.PROCESSING.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Return must be approved or "
                "processing before replacement"
            ),
        )

    return_item = next(
        (
            item
            for item in sales_return.items
            if item.id
            == payload.return_item_id
        ),
        None,
    )

    if return_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return item was not found",
        )

    if (
        return_item
        .replacement_stock_movement_id
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Replacement has already been "
                "issued for this return item"
            ),
        )

    product = await session.get(
        Product,
        payload.replacement_product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Replacement product was not found"
            ),
        )

    if (
        product.company_id
        != sales_return.company_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Replacement product belongs "
                "to another company"
            ),
        )

    warehouse = await session.get(
        Warehouse,
        payload.warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Replacement warehouse was not found"
            ),
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Replacement warehouse is inactive"
            ),
        )

    if (
        warehouse.branch_id
        != sales_return.branch_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Replacement warehouse belongs "
                "to another branch"
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
                "Replacement stock balance "
                "does not exist"
            ),
        )

    available = qty(
        Decimal(
            stock_item.quantity_on_hand
        )
        - Decimal(
            stock_item.quantity_reserved
        )
    )

    replacement_qty = qty(
        return_item.quantity
    )

    return_before_snapshot = (
        sales_return_audit_snapshot(
            sales_return
        )
    )

    replacement_item_before = {
        "id":
            return_item.id,
        "return_id":
            return_item.return_id,
        "product_id":
            return_item.product_id,
        "quantity":
            str(qty(
                return_item.quantity
            )),
        "replacement_product_id":
            return_item.replacement_product_id,
        "replacement_serial_number_id":
            return_item
            .replacement_serial_number_id,
        "replacement_stock_movement_id":
            return_item
            .replacement_stock_movement_id,
    }

    stock_before = {
        "id":
            stock_item.id,
        "warehouse_id":
            stock_item.warehouse_id,
        "product_id":
            stock_item.product_id,
        "quantity_on_hand":
            str(qty(
                stock_item.quantity_on_hand
            )),
        "quantity_reserved":
            str(qty(
                stock_item.quantity_reserved
            )),
        "average_cost":
            str(money(
                stock_item.average_cost
            )),
    }

    now = utc_now()

    if product.track_serial_numbers:
        if (
            payload
            .replacement_serial_number_id
            is None
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Replacement serial number "
                    "is required"
                ),
            )

        if replacement_qty != ONE_3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Serialized replacement "
                    "quantity must be exactly 1"
                ),
            )

        serial = await session.get(
            ProductSerialNumber,
            payload.replacement_serial_number_id,
        )

        if serial is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Replacement serial number "
                    "was not found"
                ),
            )

        if serial.product_id != product.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Replacement serial does not "
                    "belong to selected product"
                ),
            )

        if serial.status != (
            SerialNumberStatus.AVAILABLE.value
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Replacement serial is "
                    "not available"
                ),
            )

        if (
            serial.warehouse_id
            != warehouse.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Replacement serial is not "
                    "inside selected warehouse"
                ),
            )

        if available < ONE_3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Insufficient replacement stock"
                ),
            )

        stock_item.quantity_on_hand = qty(
            Decimal(
                stock_item.quantity_on_hand
            )
            - ONE_3
        )

        serial.status = (
            SerialNumberStatus
            .REPLACEMENT_ISSUED.value
        )

        serial.current_customer_id = (
            sales_return.customer_id
        )

        serial.warranty_start_date = (
            now.date()
        )

        serial.warranty_end_date = (
            add_months(
                now.date(),
                product.warranty_months,
            )
            if product.warranty_months > 0
            else None
        )

        serial.sold_at = now
        serial.warehouse_id = None

        movement_quantity = -ONE_3

        movement_serial_id = serial.id

    else:
        if (
            payload
            .replacement_serial_number_id
            is not None
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail=(
                    "Non-serialized replacement "
                    "must not include a serial number"
                ),
            )

        if replacement_qty > available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Insufficient replacement stock. "
                    f"Available: {available}"
                ),
            )

        stock_item.quantity_on_hand = qty(
            Decimal(
                stock_item.quantity_on_hand
            )
            - replacement_qty
        )

        movement_quantity = (
            -replacement_qty
        )

        movement_serial_id = None

    movement = StockMovement(
        company_id=sales_return.company_id,
        branch_id=sales_return.branch_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        serial_number_id=movement_serial_id,
        movement_type=(
            StockMovementType
            .REPLACEMENT_ISSUE.value
        ),
        quantity=movement_quantity,
        unit_cost=stock_item.average_cost,
        reference_type="sales_return",
        reference_id=(
            sales_return.return_number
        ),
        notes=(
            payload.notes
            or (
                "Replacement issued for "
                f"{sales_return.return_number}"
            )
        ),
        created_by_id=current_user.id,
    )

    session.add(movement)

    try:
        await session.flush()

        return_item.replacement_product_id = (
            product.id
        )

        return_item.replacement_serial_number_id = (
            payload.replacement_serial_number_id
        )

        return_item.replacement_stock_movement_id = (
            movement.id
        )

        if payload.notes is not None:
            return_item.notes = (
                payload.notes
            )

        if sales_return.status == (
            ReturnStatus.APPROVED.value
        ):
            await receive_returned_stock(
                session,
                sales_return,
                current_user,
            )

            old_status = sales_return.status

            sales_return.status = (
                ReturnStatus.PROCESSING.value
            )

            await add_status_history(
                session,
                sales_return=sales_return,
                old_status=old_status,
                new_status=(
                    ReturnStatus
                    .PROCESSING.value
                ),
                current_user=current_user,
                remarks=(
                    "Returned stock received "
                    "and replacement processing started"
                ),
            )

        replacement_complete = all(
            (
                item
                .replacement_stock_movement_id
                is not None
            )
            for item in sales_return.items
        )

        if replacement_complete:
            old_status = sales_return.status

            sales_return.status = (
                ReturnStatus.COMPLETED.value
            )

            sales_return.completed_at = (
                utc_now()
            )

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
                    "All replacement items issued"
                ),
            )

        sales_return.updated_by_id = (
            current_user.id
        )

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="return.replacement_issued",
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=(
                f"Replacement issued for "
                f"{sales_return.return_number}"
            ),
            before_data={
                "return":
                    return_before_snapshot,
                "return_item":
                    replacement_item_before,
                "stock":
                    stock_before,
            },
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
                "return_item": {
                    "id":
                        return_item.id,
                    "return_id":
                        return_item.return_id,
                    "product_id":
                        return_item.product_id,
                    "quantity":
                        str(qty(
                            return_item.quantity
                        )),
                    "replacement_product_id":
                        return_item
                        .replacement_product_id,
                    "replacement_serial_number_id":
                        return_item
                        .replacement_serial_number_id,
                    "replacement_stock_movement_id":
                        return_item
                        .replacement_stock_movement_id,
                },
                "stock": {
                    "id":
                        stock_item.id,
                    "warehouse_id":
                        stock_item.warehouse_id,
                    "product_id":
                        stock_item.product_id,
                    "quantity_on_hand":
                        str(qty(
                            stock_item
                            .quantity_on_hand
                        )),
                    "quantity_reserved":
                        str(qty(
                            stock_item
                            .quantity_reserved
                        )),
                    "average_cost":
                        str(money(
                            stock_item.average_cost
                        )),
                },
                "movement": {
                    "id":
                        movement.id,
                    "movement_type":
                        movement.movement_type,
                    "warehouse_id":
                        movement.warehouse_id,
                    "product_id":
                        movement.product_id,
                    "serial_number_id":
                        movement.serial_number_id,
                    "quantity":
                        str(qty(
                            movement.quantity
                        )),
                    "unit_cost":
                        str(money(
                            movement.unit_cost
                        )),
                    "reference_type":
                        movement.reference_type,
                    "reference_id":
                        movement.reference_id,
                },
            },
            metadata={
                "return_item_id":
                    return_item.id,
                "replacement_product_id":
                    product.id,
                "replacement_serial_number_id":
                    payload
                    .replacement_serial_number_id,
                "replacement_stock_movement_id":
                    movement.id,
                "warehouse_id":
                    warehouse.id,
                "replacement_quantity":
                    str(replacement_qty),
                "return_status":
                    sales_return.status,
                "replacement_complete":
                    replacement_complete,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        return_id,
    )


async def change_return_status(
    session: AsyncSession,
    return_id: int,
    payload: ReturnStatusChangeRequest,
    current_user: User,
) -> SalesReturn:
    sales_return = await get_return(
        session,
        return_id,
    )

    old_status = sales_return.status
    new_status = payload.new_status.value

    return_before_snapshot = (
        sales_return_audit_snapshot(
            sales_return
        )
    )

    if old_status in {
        ReturnStatus.REJECTED.value,
        ReturnStatus.COMPLETED.value,
        ReturnStatus.CANCELLED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This return is already in a "
                "terminal status"
            ),
        )

    if new_status in {
        ReturnStatus.APPROVED.value,
        ReturnStatus.REJECTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Use the approval action to approve "
                "or reject a return"
            ),
        )

    allowed_transitions = {
        ReturnStatus.REQUESTED.value: {
            ReturnStatus.INSPECTION.value,
            ReturnStatus.CANCELLED.value,
        },
        ReturnStatus.INSPECTION.value: {
            ReturnStatus.WAITING_APPROVAL.value,
            ReturnStatus.CANCELLED.value,
        },
        ReturnStatus.WAITING_APPROVAL.value: {
            ReturnStatus.CANCELLED.value,
        },
        ReturnStatus.APPROVED.value: {
            ReturnStatus.PROCESSING.value,
            ReturnStatus.CANCELLED.value,
        },
        ReturnStatus.PROCESSING.value: {
            ReturnStatus.COMPLETED.value,
        },
    }

    if new_status not in (
        allowed_transitions.get(
            old_status,
            set(),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Return status cannot change "
                f"from {old_status} "
                f"to {new_status}"
            ),
        )

    if (
        new_status
        == ReturnStatus.PROCESSING.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Use the process-return action "
                "to start return processing"
            ),
        )

    if (
        new_status
        == ReturnStatus.COMPLETED.value
    ):
        if sales_return.resolution == (
            ReturnResolution.REPLACEMENT.value
        ):
            replacement_complete = all(
                (
                    item
                    .replacement_stock_movement_id
                    is not None
                )
                for item
                in sales_return.items
            )

            if not replacement_complete:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "All replacement items "
                        "must be issued first"
                    ),
                )

        if sales_return.resolution in {
            ReturnResolution.REFUND.value,
            ReturnResolution.STORE_CREDIT.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Financial return cannot be "
                    "completed until the refund/"
                    "credit-note ledger is implemented"
                ),
            )

        sales_return.completed_at = (
            utc_now()
        )

    sales_return.status = new_status
    sales_return.updated_by_id = (
        current_user.id
    )

    await add_status_history(
        session,
        sales_return=sales_return,
        old_status=old_status,
        new_status=new_status,
        current_user=current_user,
        remarks=payload.remarks,
    )

    try:
        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="return.status_changed",
            module="returns",
            entity_type="sales_return",
            entity_id=sales_return.id,
            entity_reference=(
                sales_return.return_number
            ),
            description=(
                f"Sales return "
                f"{sales_return.return_number} "
                f"status changed from "
                f"{old_status} to {new_status}"
            ),
            before_data={
                "return":
                    return_before_snapshot,
            },
            after_data={
                "return":
                    sales_return_audit_snapshot(
                        sales_return
                    ),
            },
            metadata={
                "old_status":
                    old_status,
                "new_status":
                    new_status,
                "remarks":
                    payload.remarks,
                "invoice_id":
                    sales_return.invoice_id,
                "customer_id":
                    sales_return.customer_id,
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    return await get_return(
        session,
        return_id,
    )


async def build_return_detail(
    session: AsyncSession,
    sales_return: SalesReturn,
) -> SalesReturnDetailResponse:
    customer = await session.get(
        Customer,
        sales_return.customer_id,
    )

    invoice = await session.get(
        SalesInvoice,
        sales_return.invoice_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return customer was not found",
        )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return invoice was not found",
        )

    return SalesReturnDetailResponse(
        id=sales_return.id,
        company_id=sales_return.company_id,
        branch_id=sales_return.branch_id,
        return_number=(
            sales_return.return_number
        ),
        invoice_id=sales_return.invoice_id,
        customer_id=sales_return.customer_id,
        return_type=sales_return.return_type,
        status=sales_return.status,
        resolution=sales_return.resolution,
        reason=sales_return.reason,
        inspection_notes=(
            sales_return.inspection_notes
        ),
        approval_notes=(
            sales_return.approval_notes
        ),
        subtotal=sales_return.subtotal,
        refund_amount=(
            sales_return.refund_amount
        ),
        approved_by_id=(
            sales_return.approved_by_id
        ),
        approved_at=sales_return.approved_at,
        completed_at=(
            sales_return.completed_at
        ),
        created_by_id=(
            sales_return.created_by_id
        ),
        updated_by_id=(
            sales_return.updated_by_id
        ),
        created_at=sales_return.created_at,
        updated_at=sales_return.updated_at,
        invoice_number=(
            invoice.invoice_number
        ),
        customer_name=customer.full_name,
        customer_phone=(
            customer.primary_phone
        ),
        items=sales_return.items,
        status_history=(
            sales_return.status_history
        ),
    )


async def list_returns(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    return_status: str | None,
    return_type: str | None,
    resolution: str | None,
) -> SalesReturnListResponse:
    filters = []

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                SalesReturn
                .return_number.ilike(
                    pattern
                ),
                Customer.full_name.ilike(
                    pattern
                ),
                Customer.primary_phone.ilike(
                    pattern
                ),
                SalesInvoice
                .invoice_number.ilike(
                    pattern
                ),
            )
        )

    if return_status is not None:
        filters.append(
            SalesReturn.status
            == return_status
        )

    if return_type is not None:
        filters.append(
            SalesReturn.return_type
            == return_type
        )

    if resolution is not None:
        filters.append(
            SalesReturn.resolution
            == resolution
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(SalesReturn)
            .join(
                Customer,
                Customer.id
                == SalesReturn.customer_id,
            )
            .join(
                SalesInvoice,
                SalesInvoice.id
                == SalesReturn.invoice_id,
            )
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(SalesReturn)
        .options(
            selectinload(
                SalesReturn.items
            ),
            selectinload(
                SalesReturn.status_history
            ),
        )
        .join(
            Customer,
            Customer.id
            == SalesReturn.customer_id,
        )
        .join(
            SalesInvoice,
            SalesInvoice.id
            == SalesReturn.invoice_id,
        )
        .where(*filters)
        .order_by(
            SalesReturn.id.desc()
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

    response_items = [
        await build_return_detail(
            session,
            record,
        )
        for record in records
    ]

    return SalesReturnListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(
            ceil(total / page_size)
            if total
            else 0
        ),
    )
