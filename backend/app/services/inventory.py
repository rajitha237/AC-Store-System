from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit import create_audit_log
from app.models import (
    Company,
    Customer,
    Product,
    ProductSerialNumber,
    SerialNumberStatus,
    StockItem,
    StockMovement,
    StockMovementType,
    Supplier,
    User,
    Warehouse,
)
from app.schemas.inventory import (
    NonSerializedStockIssueRequest,
    NonSerializedStockIssueResponse,
    NonSerializedStockReceiveRequest,
    NonSerializedStockReceiveResponse,
    SerialNumberDetailResponse,
    SerializedStockIssueRequest,
    SerializedStockIssueResponse,
    SerializedStockReceiveRequest,
    SerializedStockReceiveResponse,
    StockBalanceResponse,
    StockMovementListResponse,
    StockMovementResponse,
)


def add_months(
    source_date: date,
    months: int,
) -> date:
    month_index = (
        source_date.month - 1 + months
    )

    year = source_date.year + month_index // 12
    month = month_index % 12 + 1

    last_day = calendar.monthrange(
        year,
        month,
    )[1]

    day = min(source_date.day, last_day)

    return date(
        year=year,
        month=month,
        day=day,
    )


def stock_item_audit_snapshot(
    stock_item: StockItem,
) -> dict:
    return {
        "warehouse_id":
            stock_item.warehouse_id,
        "product_id":
            stock_item.product_id,
        "quantity_on_hand":
            stock_item.quantity_on_hand,
        "quantity_reserved":
            stock_item.quantity_reserved,
        "average_cost":
            stock_item.average_cost,
    }


def stock_movement_audit_snapshot(
    movement: StockMovement,
) -> dict:
    return {
        "id":
            movement.id,
        "company_id":
            movement.company_id,
        "branch_id":
            movement.branch_id,
        "warehouse_id":
            movement.warehouse_id,
        "product_id":
            movement.product_id,
        "serial_number_id":
            movement.serial_number_id,
        "movement_type":
            movement.movement_type,
        "quantity":
            movement.quantity,
        "unit_cost":
            movement.unit_cost,
        "reference_type":
            movement.reference_type,
        "reference_id":
            movement.reference_id,
    }


def serial_number_audit_snapshot(
    serial_record: ProductSerialNumber,
) -> dict:
    return {
        "id":
            serial_record.id,
        "product_id":
            serial_record.product_id,
        "serial_number":
            serial_record.serial_number,
        "warehouse_id":
            serial_record.warehouse_id,
        "supplier_id":
            serial_record.supplier_id,
        "status":
            serial_record.status,
        "current_customer_id":
            serial_record.current_customer_id,
        "warranty_start_date":
            serial_record.warranty_start_date,
        "warranty_end_date":
            serial_record.warranty_end_date,
        "received_at":
            serial_record.received_at,
        "sold_at":
            serial_record.sold_at,
    }


async def get_active_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(Company.is_active.is_(True))
        .order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active company record is not configured",
        )

    return company


async def get_product_or_404(
    session: AsyncSession,
    product_id: int,
) -> Product:
    product = await session.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product was not found",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected product is inactive",
        )

    return product


async def get_warehouse_or_404(
    session: AsyncSession,
    warehouse_id: int,
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

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected warehouse is inactive",
        )

    return warehouse


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

    if customer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected customer is not active",
        )

    return customer


async def validate_supplier(
    session: AsyncSession,
    supplier_id: int | None,
) -> Supplier | None:
    if supplier_id is None:
        return None

    supplier = await session.get(
        Supplier,
        supplier_id,
    )

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier was not found",
        )

    if not supplier.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected supplier is inactive",
        )

    return supplier


async def get_stock_item_or_404(
    session: AsyncSession,
    *,
    warehouse_id: int,
    product_id: int,
) -> StockItem:
    result = await session.execute(
        select(StockItem).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id == product_id,
        )
    )
    stock_item = result.scalar_one_or_none()

    if stock_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "A stock balance does not exist for this "
                "product and warehouse"
            ),
        )

    return stock_item


async def get_or_create_stock_item(
    session: AsyncSession,
    *,
    warehouse_id: int,
    product_id: int,
) -> StockItem:
    result = await session.execute(
        select(StockItem).where(
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id == product_id,
        )
    )
    stock_item = result.scalar_one_or_none()

    if stock_item is None:
        stock_item = StockItem(
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity_on_hand=Decimal("0.000"),
            quantity_reserved=Decimal("0.000"),
            average_cost=Decimal("0.00"),
        )
        session.add(stock_item)
        await session.flush()

    return stock_item


def calculate_weighted_average_cost(
    *,
    old_quantity: Decimal,
    old_average_cost: Decimal,
    received_quantity: Decimal,
    received_unit_cost: Decimal,
) -> Decimal:
    new_quantity = old_quantity + received_quantity

    if new_quantity <= Decimal("0.000"):
        return Decimal("0.00")

    old_value = old_quantity * old_average_cost
    received_value = received_quantity * received_unit_cost

    return (
        (old_value + received_value) / new_quantity
    ).quantize(Decimal("0.01"))


async def validate_serial_duplicates(
    session: AsyncSession,
    *,
    company_id: int,
    primary_serials: list[str],
    secondary_serials: list[str],
) -> None:
    all_serials = list(
        set(primary_serials + secondary_serials)
    )

    if not all_serials:
        return

    result = await session.execute(
        select(ProductSerialNumber).where(
            ProductSerialNumber.company_id == company_id,
            or_(
                ProductSerialNumber.serial_number.in_(
                    all_serials
                ),
                ProductSerialNumber.secondary_serial_number.in_(
                    all_serials
                ),
            ),
        )
    )

    duplicate = result.scalars().first()

    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Serial number already exists: "
                f"{duplicate.serial_number}"
            ),
        )


async def receive_serialized_stock(
    session: AsyncSession,
    payload: SerializedStockReceiveRequest,
    current_user: User,
) -> SerializedStockReceiveResponse:
    company = await get_active_company(session)
    product = await get_product_or_404(
        session,
        payload.product_id,
    )
    warehouse = await get_warehouse_or_404(
        session,
        payload.warehouse_id,
    )

    await validate_supplier(
        session,
        payload.supplier_id,
    )

    if product.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product belongs to another company",
        )

    if not product.track_serial_numbers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product does not use serial-number "
                "tracking"
            ),
        )

    primary_serials = [
        serial.serial_number
        for serial in payload.serials
    ]

    secondary_serials = [
        serial.secondary_serial_number
        for serial in payload.serials
        if serial.secondary_serial_number is not None
    ]

    await validate_serial_duplicates(
        session=session,
        company_id=company.id,
        primary_serials=primary_serials,
        secondary_serials=secondary_serials,
    )

    stock_item = await get_or_create_stock_item(
        session=session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    received_quantity = Decimal(
        str(len(payload.serials))
    )

    old_quantity = Decimal(
        stock_item.quantity_on_hand
    )
    old_average_cost = Decimal(
        stock_item.average_cost
    )

    stock_item.average_cost = (
        calculate_weighted_average_cost(
            old_quantity=old_quantity,
            old_average_cost=old_average_cost,
            received_quantity=received_quantity,
            received_unit_cost=payload.unit_cost,
        )
    )

    stock_item.quantity_on_hand = (
        old_quantity + received_quantity
    )

    received_at = datetime.now(timezone.utc)
    created_serials: list[ProductSerialNumber] = []

    try:
        for serial_input in payload.serials:
            serial_record = ProductSerialNumber(
                company_id=company.id,
                product_id=product.id,
                serial_number=serial_input.serial_number,
                secondary_serial_number=(
                    serial_input.secondary_serial_number
                ),
                warehouse_id=warehouse.id,
                supplier_id=payload.supplier_id,
                status=SerialNumberStatus.AVAILABLE.value,
                received_at=received_at,
                notes=serial_input.notes,
                created_by_id=current_user.id,
            )

            session.add(serial_record)
            await session.flush()

            movement = StockMovement(
                company_id=company.id,
                branch_id=warehouse.branch_id,
                warehouse_id=warehouse.id,
                product_id=product.id,
                serial_number_id=serial_record.id,
                movement_type=(
                    StockMovementType.PURCHASE_RECEIPT.value
                    if payload.reference_type
                    == "purchase_receipt"
                    else StockMovementType.OPENING_BALANCE.value
                ),
                quantity=Decimal("1.000"),
                unit_cost=payload.unit_cost,
                reference_type=payload.reference_type,
                reference_id=payload.reference_id,
                notes=payload.notes,
                created_by_id=current_user.id,
            )

            session.add(movement)
            created_serials.append(serial_record)

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory.stock_received_serialized"
            ),
            module="inventory",
            entity_type="stock_movement",
            entity_id=None,
            entity_reference=(
                payload.reference_id
            ),
            description=(
                "Serialized inventory stock received"
            ),
            before_data={
                "stock": {
                    "warehouse_id":
                        stock_item.warehouse_id,
                    "product_id":
                        stock_item.product_id,
                    "quantity_on_hand":
                        old_quantity,
                    "average_cost":
                        old_average_cost,
                },
            },
            after_data={
                "stock":
                    stock_item_audit_snapshot(
                        stock_item
                    ),
                "serials": [
                    serial_number_audit_snapshot(
                        serial_record
                    )
                    for serial_record
                    in created_serials
                ],
            },
            metadata={
                "product_id":
                    product.id,
                "warehouse_id":
                    warehouse.id,
                "quantity_received":
                    received_quantity,
                "unit_cost":
                    payload.unit_cost,
                "supplier_id":
                    payload.supplier_id,
                "reference_type":
                    payload.reference_type,
                "reference_id":
                    payload.reference_id,
            },
        )

        await session.commit()

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Serialized stock could not be received. "
                "One or more serial numbers already exist"
            ),
        ) from exc

    responses = []

    for serial_record in created_serials:
        await session.refresh(serial_record)

        responses.append(
            serial_record
        )

    await session.refresh(stock_item)

    return SerializedStockReceiveResponse(
        message="Serialized stock received successfully",
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity_received=len(responses),
        quantity_on_hand=stock_item.quantity_on_hand,
        average_cost=stock_item.average_cost,
        serials=responses,
    )


async def receive_non_serialized_stock(
    session: AsyncSession,
    payload: NonSerializedStockReceiveRequest,
    current_user: User,
) -> NonSerializedStockReceiveResponse:
    company = await get_active_company(session)
    product = await get_product_or_404(
        session,
        payload.product_id,
    )
    warehouse = await get_warehouse_or_404(
        session,
        payload.warehouse_id,
    )

    await validate_supplier(
        session,
        payload.supplier_id,
    )

    if product.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product belongs to another company",
        )

    if product.track_serial_numbers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product requires individual serial "
                "numbers"
            ),
        )

    stock_item = await get_or_create_stock_item(
        session=session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    old_quantity = Decimal(
        stock_item.quantity_on_hand
    )
    old_average_cost = Decimal(
        stock_item.average_cost
    )

    stock_item.average_cost = (
        calculate_weighted_average_cost(
            old_quantity=old_quantity,
            old_average_cost=old_average_cost,
            received_quantity=payload.quantity,
            received_unit_cost=payload.unit_cost,
        )
    )

    stock_item.quantity_on_hand = (
        old_quantity + payload.quantity
    )

    movement = StockMovement(
        company_id=company.id,
        branch_id=warehouse.branch_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        serial_number_id=None,
        movement_type=(
            StockMovementType.PURCHASE_RECEIPT.value
            if payload.reference_type
            == "purchase_receipt"
            else StockMovementType.OPENING_BALANCE.value
        ),
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(movement)

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory."
                "stock_received_non_serialized"
            ),
            module="inventory",
            entity_type="stock_movement",
            entity_id=movement.id,
            entity_reference=(
                payload.reference_id
            ),
            description=(
                "Non-serialized inventory "
                "stock received"
            ),
            before_data={
                "stock": {
                    "warehouse_id":
                        stock_item.warehouse_id,
                    "product_id":
                        stock_item.product_id,
                    "quantity_on_hand":
                        old_quantity,
                    "average_cost":
                        old_average_cost,
                },
            },
            after_data={
                "stock":
                    stock_item_audit_snapshot(
                        stock_item
                    ),
                "movement":
                    stock_movement_audit_snapshot(
                        movement
                    ),
            },
            metadata={
                "product_id":
                    product.id,
                "warehouse_id":
                    warehouse.id,
                "quantity_received":
                    payload.quantity,
                "unit_cost":
                    payload.unit_cost,
                "supplier_id":
                    payload.supplier_id,
                "reference_type":
                    payload.reference_type,
                "reference_id":
                    payload.reference_id,
            },
        )

        await session.commit()
        await session.refresh(stock_item)
        await session.refresh(movement)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock could not be received",
        ) from exc

    quantity_available = (
        stock_item.quantity_on_hand
        - stock_item.quantity_reserved
    )

    return NonSerializedStockReceiveResponse(
        message="Non-serialized stock received successfully",
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity_received=payload.quantity,
        quantity_on_hand=stock_item.quantity_on_hand,
        quantity_available=quantity_available,
        average_cost=stock_item.average_cost,
        movement=movement,
    )


async def build_serial_detail(
    session: AsyncSession,
    serial_record: ProductSerialNumber,
) -> SerialNumberDetailResponse:
    product = await session.get(
        Product,
        serial_record.product_id,
    )

    warehouse = None

    if serial_record.warehouse_id is not None:
        warehouse = await session.get(
            Warehouse,
            serial_record.warehouse_id,
        )

    supplier = None

    if serial_record.supplier_id is not None:
        supplier = await session.get(
            Supplier,
            serial_record.supplier_id,
        )

    customer = None

    if serial_record.current_customer_id is not None:
        customer = await session.get(
            Customer,
            serial_record.current_customer_id,
        )

    return SerialNumberDetailResponse(
        id=serial_record.id,
        company_id=serial_record.company_id,
        product_id=serial_record.product_id,
        serial_number=serial_record.serial_number,
        secondary_serial_number=(
            serial_record.secondary_serial_number
        ),
        warehouse_id=serial_record.warehouse_id,
        supplier_id=serial_record.supplier_id,
        status=serial_record.status,
        current_customer_id=(
            serial_record.current_customer_id
        ),
        warranty_start_date=(
            serial_record.warranty_start_date
        ),
        warranty_end_date=(
            serial_record.warranty_end_date
        ),
        received_at=serial_record.received_at,
        sold_at=serial_record.sold_at,
        notes=serial_record.notes,
        created_by_id=serial_record.created_by_id,
        created_at=serial_record.created_at,
        updated_at=serial_record.updated_at,
        product_code=product.product_code,
        product_name=product.name,
        model_number=product.model_number,
        warehouse_code=(
            warehouse.code
            if warehouse is not None
            else None
        ),
        warehouse_name=(
            warehouse.name
            if warehouse is not None
            else None
        ),
        supplier_name=(
            supplier.company_name
            if supplier is not None
            else None
        ),
        customer_name=(
            customer.full_name
            if customer is not None
            else None
        ),
        customer_phone=(
            customer.primary_phone
            if customer is not None
            else None
        ),
    )


async def list_serial_numbers(
    session: AsyncSession,
    *,
    search: str | None,
    product_id: int | None,
    warehouse_id: int | None,
    serial_status: str | None,
) -> list[SerialNumberDetailResponse]:
    filters = []

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                ProductSerialNumber.serial_number.ilike(
                    pattern
                ),
                ProductSerialNumber
                .secondary_serial_number.ilike(pattern),
            )
        )

    if product_id is not None:
        filters.append(
            ProductSerialNumber.product_id == product_id
        )

    if warehouse_id is not None:
        filters.append(
            ProductSerialNumber.warehouse_id
            == warehouse_id
        )

    if serial_status is not None:
        filters.append(
            ProductSerialNumber.status == serial_status
        )

    result = await session.execute(
        select(ProductSerialNumber)
        .where(*filters)
        .order_by(
            ProductSerialNumber.created_at.desc(),
            ProductSerialNumber.id.desc(),
        )
    )

    records = result.scalars().all()

    return [
        await build_serial_detail(session, record)
        for record in records
    ]


async def get_serial_or_404(
    session: AsyncSession,
    serial_number_id: int,
) -> ProductSerialNumber:
    serial_record = await session.get(
        ProductSerialNumber,
        serial_number_id,
    )

    if serial_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Serial-number record was not found",
        )

    return serial_record


async def issue_serialized_stock(
    session: AsyncSession,
    payload: SerializedStockIssueRequest,
    current_user: User,
) -> SerializedStockIssueResponse:
    serial_record = await get_serial_or_404(
        session,
        payload.serial_number_id,
    )

    product = await get_product_or_404(
        session,
        serial_record.product_id,
    )

    customer = await get_customer_or_404(
        session,
        payload.customer_id,
    )

    if serial_record.status != (
        SerialNumberStatus.AVAILABLE.value
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only an available serial number can be "
                f"issued. Current status: "
                f"{serial_record.status}"
            ),
        )

    if serial_record.warehouse_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Serial number is not assigned to a "
                "warehouse"
            ),
        )

    warehouse = await get_warehouse_or_404(
        session,
        serial_record.warehouse_id,
    )

    stock_item = await get_stock_item_or_404(
        session=session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    available_quantity = (
        Decimal(stock_item.quantity_on_hand)
        - Decimal(stock_item.quantity_reserved)
    )

    if available_quantity < Decimal("1.000"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient available stock for this "
                "serialized product"
            ),
        )

    warranty_start = (
        payload.warranty_start_date
        or datetime.now(timezone.utc).date()
    )

    warranty_end = None

    if product.warranty_months > 0:
        warranty_end = add_months(
            warranty_start,
            product.warranty_months,
        )

    original_warehouse_id = warehouse.id

    stock_before = (
        stock_item_audit_snapshot(
            stock_item
        )
    )

    serial_before = (
        serial_number_audit_snapshot(
            serial_record
        )
    )

    stock_item.quantity_on_hand = (
        Decimal(stock_item.quantity_on_hand)
        - Decimal("1.000")
    )

    serial_record.status = (
        SerialNumberStatus.SOLD.value
        if payload.issue_type.value == "sale"
        else (
            SerialNumberStatus.REPLACEMENT_ISSUED.value
            if payload.issue_type.value == "replacement"
            else SerialNumberStatus.SOLD.value
        )
    )

    serial_record.current_customer_id = customer.id
    serial_record.warranty_start_date = warranty_start
    serial_record.warranty_end_date = warranty_end
    serial_record.sold_at = datetime.now(timezone.utc)
    serial_record.warehouse_id = None

    movement = StockMovement(
        company_id=serial_record.company_id,
        branch_id=warehouse.branch_id,
        warehouse_id=original_warehouse_id,
        product_id=product.id,
        serial_number_id=serial_record.id,
        movement_type=(
            StockMovementType.REPLACEMENT_ISSUE.value
            if payload.issue_type.value == "replacement"
            else StockMovementType.SALE_ISSUE.value
        ),
        quantity=Decimal("-1.000"),
        unit_cost=stock_item.average_cost,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(movement)

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory.stock_issued_serialized"
            ),
            module="inventory",
            entity_type="stock_movement",
            entity_id=movement.id,
            entity_reference=(
                payload.reference_id
            ),
            description=(
                "Serialized inventory stock issued"
            ),
            before_data={
                "stock":
                    stock_before,
                "serial":
                    serial_before,
            },
            after_data={
                "stock":
                    stock_item_audit_snapshot(
                        stock_item
                    ),
                "serial":
                    serial_number_audit_snapshot(
                        serial_record
                    ),
                "movement":
                    stock_movement_audit_snapshot(
                        movement
                    ),
            },
            metadata={
                "product_id":
                    product.id,
                "warehouse_id":
                    original_warehouse_id,
                "customer_id":
                    customer.id,
                "serial_number_id":
                    serial_record.id,
                "issue_type":
                    payload.issue_type.value,
                "reference_type":
                    payload.reference_type,
                "reference_id":
                    payload.reference_id,
            },
        )

        await session.commit()
        await session.refresh(serial_record)
        await session.refresh(stock_item)
        await session.refresh(movement)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Serialized stock could not be issued",
        ) from exc

    serial_detail = await build_serial_detail(
        session,
        serial_record,
    )

    return SerializedStockIssueResponse(
        message="Serialized stock issued successfully",
        product_id=product.id,
        warehouse_id=original_warehouse_id,
        customer_id=customer.id,
        quantity_issued=Decimal("1.000"),
        quantity_on_hand=stock_item.quantity_on_hand,
        serial=serial_detail,
        movement=movement,
    )


async def issue_non_serialized_stock(
    session: AsyncSession,
    payload: NonSerializedStockIssueRequest,
    current_user: User,
) -> NonSerializedStockIssueResponse:
    company = await get_active_company(session)

    product = await get_product_or_404(
        session,
        payload.product_id,
    )

    warehouse = await get_warehouse_or_404(
        session,
        payload.warehouse_id,
    )

    if product.track_serial_numbers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product requires a serial number "
                "for stock issue"
            ),
        )

    if payload.customer_id is not None:
        await get_customer_or_404(
            session,
            payload.customer_id,
        )

    stock_item = await get_stock_item_or_404(
        session=session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    available_quantity = (
        Decimal(stock_item.quantity_on_hand)
        - Decimal(stock_item.quantity_reserved)
    )

    if payload.quantity > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient available stock. "
                f"Available quantity: "
                f"{available_quantity}"
            ),
        )

    stock_before = (
        stock_item_audit_snapshot(
            stock_item
        )
    )

    stock_item.quantity_on_hand = (
        Decimal(stock_item.quantity_on_hand)
        - payload.quantity
    )

    movement = StockMovement(
        company_id=company.id,
        branch_id=warehouse.branch_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        serial_number_id=None,
        movement_type=(
            StockMovementType.REPLACEMENT_ISSUE.value
            if payload.issue_type.value == "replacement"
            else StockMovementType.SALE_ISSUE.value
        ),
        quantity=-payload.quantity,
        unit_cost=stock_item.average_cost,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        notes=payload.notes,
        created_by_id=current_user.id,
    )

    session.add(movement)

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory."
                "stock_issued_non_serialized"
            ),
            module="inventory",
            entity_type="stock_movement",
            entity_id=movement.id,
            entity_reference=(
                payload.reference_id
            ),
            description=(
                "Non-serialized inventory "
                "stock issued"
            ),
            before_data={
                "stock":
                    stock_before,
            },
            after_data={
                "stock":
                    stock_item_audit_snapshot(
                        stock_item
                    ),
                "movement":
                    stock_movement_audit_snapshot(
                        movement
                    ),
            },
            metadata={
                "product_id":
                    product.id,
                "warehouse_id":
                    warehouse.id,
                "customer_id":
                    payload.customer_id,
                "quantity_issued":
                    payload.quantity,
                "issue_type":
                    payload.issue_type.value,
                "reference_type":
                    payload.reference_type,
                "reference_id":
                    payload.reference_id,
            },
        )

        await session.commit()
        await session.refresh(stock_item)
        await session.refresh(movement)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Non-serialized stock could not be issued",
        ) from exc

    quantity_available = (
        stock_item.quantity_on_hand
        - stock_item.quantity_reserved
    )

    return NonSerializedStockIssueResponse(
        message="Non-serialized stock issued successfully",
        product_id=product.id,
        warehouse_id=warehouse.id,
        customer_id=payload.customer_id,
        quantity_issued=payload.quantity,
        quantity_on_hand=stock_item.quantity_on_hand,
        quantity_available=quantity_available,
        average_cost=stock_item.average_cost,
        movement=movement,
    )


async def list_stock_balances(
    session: AsyncSession,
    *,
    search: str | None,
    warehouse_id: int | None,
    product_id: int | None,
    low_stock_only: bool,
) -> list[StockBalanceResponse]:
    filters = []

    if warehouse_id is not None:
        filters.append(
            StockItem.warehouse_id == warehouse_id
        )

    if product_id is not None:
        filters.append(
            StockItem.product_id == product_id
        )

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                Product.product_code.ilike(pattern),
                Product.name.ilike(pattern),
                Product.model_number.ilike(pattern),
                Product.barcode.ilike(pattern),
            )
        )

    result = await session.execute(
        select(StockItem, Product, Warehouse)
        .join(
            Product,
            Product.id == StockItem.product_id,
        )
        .join(
            Warehouse,
            Warehouse.id == StockItem.warehouse_id,
        )
        .where(*filters)
        .order_by(
            Warehouse.name,
            Product.name,
        )
    )

    balances: list[StockBalanceResponse] = []

    for stock_item, product, warehouse in result.all():
        quantity_available = (
            stock_item.quantity_on_hand
            - stock_item.quantity_reserved
        )

        is_low_stock = (
            quantity_available <= product.reorder_level
        )

        if low_stock_only and not is_low_stock:
            continue

        balances.append(
            StockBalanceResponse(
                id=stock_item.id,
                warehouse_id=warehouse.id,
                warehouse_code=warehouse.code,
                warehouse_name=warehouse.name,
                product_id=product.id,
                product_code=product.product_code,
                product_name=product.name,
                track_serial_numbers=(
                    product.track_serial_numbers
                ),
                quantity_on_hand=(
                    stock_item.quantity_on_hand
                ),
                quantity_reserved=(
                    stock_item.quantity_reserved
                ),
                quantity_available=quantity_available,
                average_cost=stock_item.average_cost,
                reorder_level=product.reorder_level,
                is_low_stock=is_low_stock,
            )
        )

    return balances


async def list_stock_movements(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    product_id: int | None,
    warehouse_id: int | None,
    serial_number_id: int | None,
    movement_type: str | None,
) -> StockMovementListResponse:
    filters = []

    if product_id is not None:
        filters.append(
            StockMovement.product_id == product_id
        )

    if warehouse_id is not None:
        filters.append(
            StockMovement.warehouse_id == warehouse_id
        )

    if serial_number_id is not None:
        filters.append(
            StockMovement.serial_number_id
            == serial_number_id
        )

    if movement_type is not None:
        filters.append(
            StockMovement.movement_type
            == movement_type
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(StockMovement)
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(StockMovement)
        .where(*filters)
        .order_by(
            StockMovement.movement_date.desc(),
            StockMovement.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    movements = result.scalars().all()

    return StockMovementListResponse(
        items=[
            StockMovementResponse.model_validate(
                movement
            )
            for movement in movements
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


async def adjust_non_serialized_stock(
    session: AsyncSession,
    payload,
    current_user: User,
):
    company = await get_active_company(
        session
    )

    product = await get_product_or_404(
        session,
        payload.product_id,
    )

    warehouse = await get_warehouse_or_404(
        session,
        payload.warehouse_id,
    )

    if product.company_id != company.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Product belongs to another company"
            ),
        )

    if product.track_serial_numbers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Serialized products cannot be "
                "quantity-adjusted. Use a "
                "serial-specific inventory operation."
            ),
        )

    stock_item = await get_stock_item_or_404(
        session=session,
        warehouse_id=warehouse.id,
        product_id=product.id,
    )

    quantity = Decimal(
        payload.quantity
    )

    quantity_on_hand = Decimal(
        stock_item.quantity_on_hand
    )

    quantity_reserved = Decimal(
        stock_item.quantity_reserved
    )

    average_cost = Decimal(
        stock_item.average_cost
    )

    quantity_available = (
        quantity_on_hand
        - quantity_reserved
    )

    direction = (
        payload.direction.value
        if hasattr(
            payload.direction,
            "value",
        )
        else str(
            payload.direction
        )
    )

    if direction == "increase":
        if payload.unit_cost is None:
            adjustment_unit_cost = (
                average_cost
            )
        else:
            adjustment_unit_cost = Decimal(
                payload.unit_cost
            )

        if (
            quantity_on_hand
            <= Decimal("0.000")
            and payload.unit_cost is None
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "unit_cost is required when "
                    "increasing stock from zero"
                ),
            )

        new_quantity = (
            quantity_on_hand
            + quantity
        )

        old_value = (
            quantity_on_hand
            * average_cost
        )

        adjustment_value = (
            quantity
            * adjustment_unit_cost
        )

        if new_quantity > Decimal("0.000"):
            new_average_cost = (
                (
                    old_value
                    + adjustment_value
                )
                / new_quantity
            ).quantize(
                Decimal("0.01")
            )
        else:
            new_average_cost = (
                average_cost
            )

        stock_item.quantity_on_hand = (
            new_quantity.quantize(
                Decimal("0.001")
            )
        )

        stock_item.average_cost = (
            new_average_cost
        )

        movement_type = (
            StockMovementType
            .ADJUSTMENT_INCREASE
            .value
        )

        movement_quantity = (
            quantity.quantize(
                Decimal("0.001")
            )
        )

        movement_unit_cost = (
            adjustment_unit_cost.quantize(
                Decimal("0.01")
            )
        )

    elif direction == "decrease":
        if quantity > quantity_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Insufficient available stock "
                    "for adjustment decrease"
                ),
            )

        stock_item.quantity_on_hand = (
            (
                quantity_on_hand
                - quantity
            ).quantize(
                Decimal("0.001")
            )
        )

        movement_type = (
            StockMovementType
            .ADJUSTMENT_DECREASE
            .value
        )

        movement_quantity = (
            -quantity
        ).quantize(
            Decimal("0.001")
        )

        movement_unit_cost = (
            average_cost.quantize(
                Decimal("0.01")
            )
        )

    else:
        raise HTTPException(
            status_code=
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Invalid stock adjustment direction"
            ),
        )

    movement_notes = (
        f"Reason: {payload.reason.strip()}"
    )

    if payload.notes:
        cleaned_notes = (
            payload.notes.strip()
        )

        if cleaned_notes:
            movement_notes += (
                f" | Notes: {cleaned_notes}"
            )

    movement = StockMovement(
        company_id=company.id,
        branch_id=warehouse.branch_id,
        warehouse_id=warehouse.id,
        product_id=product.id,
        serial_number_id=None,
        movement_type=movement_type,
        quantity=movement_quantity,
        unit_cost=movement_unit_cost,
        reference_type=
            "stock_adjustment",
        reference_id=
            payload.reference_id,
        notes=movement_notes,
        created_by_id=
            current_user.id,
    )

    session.add(
        movement
    )

    try:
        await session.flush()

        await session.commit()

        await session.refresh(
            stock_item
        )

        await session.refresh(
            movement
        )

    except Exception:
        await session.rollback()
        raise

    final_on_hand = Decimal(
        stock_item.quantity_on_hand
    )

    final_reserved = Decimal(
        stock_item.quantity_reserved
    )

    return {
        "message":
            "Stock adjustment completed",
        "product_id":
            product.id,
        "warehouse_id":
            warehouse.id,
        "direction":
            direction,
        "quantity_adjusted":
            quantity.quantize(
                Decimal("0.001")
            ),
        "quantity_on_hand":
            final_on_hand,
        "quantity_reserved":
            final_reserved,
        "quantity_available":
            (
                final_on_hand
                - final_reserved
            ),
        "average_cost":
            Decimal(
                stock_item.average_cost
            ),
        "movement":
            movement,
    }


def _inventory_transfer_notes(
    *,
    reason: str,
    notes: str | None,
) -> str:
    value = (
        f"Reason: {reason.strip()}"
    )

    if notes:
        cleaned = notes.strip()

        if cleaned:
            value += (
                f" | Notes: {cleaned}"
            )

    return value


def _stock_item_transfer_snapshot(
    stock_item: StockItem,
) -> dict:
    quantity_on_hand = Decimal(
        stock_item.quantity_on_hand
    )

    quantity_reserved = Decimal(
        stock_item.quantity_reserved
    )

    return {
        "warehouse_id":
            stock_item.warehouse_id,
        "product_id":
            stock_item.product_id,
        "quantity_on_hand":
            quantity_on_hand,
        "quantity_reserved":
            quantity_reserved,
        "quantity_available":
            (
                quantity_on_hand
                - quantity_reserved
            ),
        "average_cost":
            Decimal(
                stock_item.average_cost
            ),
    }


async def transfer_non_serialized_stock(
    session: AsyncSession,
    payload,
    current_user: User,
):
    company = await get_active_company(
        session
    )

    product = await get_product_or_404(
        session,
        payload.product_id,
    )

    source_warehouse = (
        await get_warehouse_or_404(
            session,
            payload.source_warehouse_id,
        )
    )

    destination_warehouse = (
        await get_warehouse_or_404(
            session,
            payload.destination_warehouse_id,
        )
    )

    if (
        source_warehouse.id
        == destination_warehouse.id
    ):
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Source and destination "
                "warehouses must be different"
            ),
        )

    if product.company_id != company.id:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Product belongs to another company"
            ),
        )

    if product.track_serial_numbers:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "This product requires "
                "serial-number transfer"
            ),
        )

    source_stock = (
        await get_stock_item_or_404(
            session=session,
            warehouse_id=
                source_warehouse.id,
            product_id=
                product.id,
        )
    )

    destination_stock = (
        await get_or_create_stock_item(
            session=session,
            warehouse_id=
                destination_warehouse.id,
            product_id=
                product.id,
        )
    )

    quantity = Decimal(
        payload.quantity
    ).quantize(
        Decimal("0.001")
    )

    source_on_hand = Decimal(
        source_stock.quantity_on_hand
    )

    source_reserved = Decimal(
        source_stock.quantity_reserved
    )

    source_available = (
        source_on_hand
        - source_reserved
    )

    if quantity > source_available:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient available stock "
                "for warehouse transfer"
            ),
        )

    source_average_cost = Decimal(
        source_stock.average_cost
    )

    destination_old_quantity = Decimal(
        destination_stock.quantity_on_hand
    )

    destination_old_average = Decimal(
        destination_stock.average_cost
    )

    before_source = (
        _stock_item_transfer_snapshot(
            source_stock
        )
    )

    before_destination = (
        _stock_item_transfer_snapshot(
            destination_stock
        )
    )

    destination_new_average = (
        calculate_weighted_average_cost(
            old_quantity=
                destination_old_quantity,
            old_average_cost=
                destination_old_average,
            received_quantity=
                quantity,
            received_unit_cost=
                source_average_cost,
        )
    )

    source_stock.quantity_on_hand = (
        source_on_hand
        - quantity
    )

    destination_stock.quantity_on_hand = (
        destination_old_quantity
        + quantity
    )

    destination_stock.average_cost = (
        destination_new_average
    )

    movement_notes = (
        _inventory_transfer_notes(
            reason=payload.reason,
            notes=payload.notes,
        )
    )

    transfer_out = StockMovement(
        company_id=company.id,
        branch_id=
            source_warehouse.branch_id,
        warehouse_id=
            source_warehouse.id,
        product_id=
            product.id,
        serial_number_id=None,
        movement_type=(
            StockMovementType
            .TRANSFER_OUT.value
        ),
        quantity=-quantity,
        unit_cost=
            source_average_cost,
        reference_type=
            "warehouse_transfer",
        reference_id=
            payload.reference_id,
        notes=movement_notes,
        created_by_id=
            current_user.id,
    )

    transfer_in = StockMovement(
        company_id=company.id,
        branch_id=
            destination_warehouse.branch_id,
        warehouse_id=
            destination_warehouse.id,
        product_id=
            product.id,
        serial_number_id=None,
        movement_type=(
            StockMovementType
            .TRANSFER_IN.value
        ),
        quantity=quantity,
        unit_cost=
            source_average_cost,
        reference_type=
            "warehouse_transfer",
        reference_id=
            payload.reference_id,
        notes=movement_notes,
        created_by_id=
            current_user.id,
    )

    session.add_all([
        transfer_out,
        transfer_in,
    ])

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory."
                "stock_transferred_non_serialized"
            ),
            module="inventory",
            entity_type=
                "stock_transfer",
            entity_id=
                transfer_out.id,
            entity_reference=
                payload.reference_id,
            description=(
                "Non-serialized inventory "
                "transferred between warehouses"
            ),
            before_data={
                "source":
                    before_source,
                "destination":
                    before_destination,
            },
            after_data={
                "source":
                    _stock_item_transfer_snapshot(
                        source_stock
                    ),
                "destination":
                    _stock_item_transfer_snapshot(
                        destination_stock
                    ),
                "transfer_out_movement_id":
                    transfer_out.id,
                "transfer_in_movement_id":
                    transfer_in.id,
            },
            metadata={
                "product_id":
                    product.id,
                "source_warehouse_id":
                    source_warehouse.id,
                "destination_warehouse_id":
                    destination_warehouse.id,
                "quantity":
                    quantity,
                "unit_cost":
                    source_average_cost,
            },
        )

        await session.commit()

        await session.refresh(
            source_stock
        )

        await session.refresh(
            destination_stock
        )

        await session.refresh(
            transfer_out
        )

        await session.refresh(
            transfer_in
        )

    except Exception:
        await session.rollback()
        raise

    final_source_on_hand = Decimal(
        source_stock.quantity_on_hand
    )

    final_source_reserved = Decimal(
        source_stock.quantity_reserved
    )

    final_destination_on_hand = Decimal(
        destination_stock.quantity_on_hand
    )

    final_destination_reserved = Decimal(
        destination_stock.quantity_reserved
    )

    return {
        "message":
            "Warehouse transfer completed",
        "product_id":
            product.id,
        "source_warehouse_id":
            source_warehouse.id,
        "destination_warehouse_id":
            destination_warehouse.id,
        "quantity_transferred":
            quantity,
        "source_quantity_on_hand":
            final_source_on_hand,
        "source_quantity_reserved":
            final_source_reserved,
        "source_quantity_available":
            (
                final_source_on_hand
                - final_source_reserved
            ),
        "destination_quantity_on_hand":
            final_destination_on_hand,
        "destination_quantity_reserved":
            final_destination_reserved,
        "destination_quantity_available":
            (
                final_destination_on_hand
                - final_destination_reserved
            ),
        "destination_average_cost":
            Decimal(
                destination_stock.average_cost
            ),
        "transfer_out_movement":
            transfer_out,
        "transfer_in_movement":
            transfer_in,
    }


async def transfer_serialized_stock(
    session: AsyncSession,
    payload,
    current_user: User,
):
    company = await get_active_company(
        session
    )

    product = await get_product_or_404(
        session,
        payload.product_id,
    )

    source_warehouse = (
        await get_warehouse_or_404(
            session,
            payload.source_warehouse_id,
        )
    )

    destination_warehouse = (
        await get_warehouse_or_404(
            session,
            payload.destination_warehouse_id,
        )
    )

    if (
        source_warehouse.id
        == destination_warehouse.id
    ):
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Source and destination "
                "warehouses must be different"
            ),
        )

    if product.company_id != company.id:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Product belongs to another company"
            ),
        )

    if not product.track_serial_numbers:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "This product does not use "
                "serial-number tracking"
            ),
        )

    serial_ids = list(
        dict.fromkeys(
            payload.serial_number_ids
        )
    )

    if (
        len(serial_ids)
        != len(
            payload.serial_number_ids
        )
    ):
        raise HTTPException(
            status_code=
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Duplicate serial number IDs "
                "are not allowed"
            ),
        )

    result = await session.execute(
        select(
            ProductSerialNumber
        )
        .where(
            ProductSerialNumber.id.in_(
                serial_ids
            )
        )
        .with_for_update()
    )

    serial_records = (
        result.scalars().all()
    )

    if (
        len(serial_records)
        != len(serial_ids)
    ):
        found_ids = {
            serial.id
            for serial
            in serial_records
        }

        missing_ids = [
            serial_id
            for serial_id
            in serial_ids
            if serial_id
            not in found_ids
        ]

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=(
                "Serial number IDs not found: "
                + ", ".join(
                    str(value)
                    for value
                    in missing_ids
                )
            ),
        )

    for serial in serial_records:
        if (
            serial.company_id
            != company.id
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_409_CONFLICT,
                detail=(
                    "Serial belongs to "
                    "another company"
                ),
            )

        if (
            serial.product_id
            != product.id
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_409_CONFLICT,
                detail=(
                    "Serial does not belong "
                    "to selected product"
                ),
            )

        if (
            serial.warehouse_id
            != source_warehouse.id
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_409_CONFLICT,
                detail=(
                    f"Serial {serial.serial_number} "
                    "is not in the selected "
                    "source warehouse"
                ),
            )

        if (
            serial.status
            != SerialNumberStatus
                .AVAILABLE.value
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_409_CONFLICT,
                detail=(
                    f"Serial {serial.serial_number} "
                    "is not available for transfer"
                ),
            )

        if (
            serial.current_customer_id
            is not None
        ):
            raise HTTPException(
                status_code=
                    status.HTTP_409_CONFLICT,
                detail=(
                    f"Serial {serial.serial_number} "
                    "is assigned to a customer"
                ),
            )

    source_stock = (
        await get_stock_item_or_404(
            session=session,
            warehouse_id=
                source_warehouse.id,
            product_id=
                product.id,
        )
    )

    destination_stock = (
        await get_or_create_stock_item(
            session=session,
            warehouse_id=
                destination_warehouse.id,
            product_id=
                product.id,
        )
    )

    quantity = Decimal(
        str(
            len(
                serial_records
            )
        )
    ).quantize(
        Decimal("0.001")
    )

    source_on_hand = Decimal(
        source_stock.quantity_on_hand
    )

    source_reserved = Decimal(
        source_stock.quantity_reserved
    )

    source_available = (
        source_on_hand
        - source_reserved
    )

    if quantity > source_available:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,
            detail=(
                "Insufficient available stock "
                "for serialized transfer"
            ),
        )

    source_average_cost = Decimal(
        source_stock.average_cost
    )

    destination_old_quantity = Decimal(
        destination_stock.quantity_on_hand
    )

    destination_old_average = Decimal(
        destination_stock.average_cost
    )

    before_source = (
        _stock_item_transfer_snapshot(
            source_stock
        )
    )

    before_destination = (
        _stock_item_transfer_snapshot(
            destination_stock
        )
    )

    serials_before = [
        {
            "id":
                serial.id,
            "serial_number":
                serial.serial_number,
            "warehouse_id":
                serial.warehouse_id,
            "status":
                serial.status,
        }
        for serial
        in serial_records
    ]

    destination_stock.average_cost = (
        calculate_weighted_average_cost(
            old_quantity=
                destination_old_quantity,
            old_average_cost=
                destination_old_average,
            received_quantity=
                quantity,
            received_unit_cost=
                source_average_cost,
        )
    )

    source_stock.quantity_on_hand = (
        source_on_hand
        - quantity
    )

    destination_stock.quantity_on_hand = (
        destination_old_quantity
        + quantity
    )

    movement_notes = (
        _inventory_transfer_notes(
            reason=payload.reason,
            notes=payload.notes,
        )
    )

    out_movements = []
    in_movements = []

    for serial in serial_records:
        serial.warehouse_id = (
            destination_warehouse.id
        )

        out_movement = StockMovement(
            company_id=
                company.id,
            branch_id=
                source_warehouse.branch_id,
            warehouse_id=
                source_warehouse.id,
            product_id=
                product.id,
            serial_number_id=
                serial.id,
            movement_type=(
                StockMovementType
                .TRANSFER_OUT.value
            ),
            quantity=
                Decimal("-1.000"),
            unit_cost=
                source_average_cost,
            reference_type=
                "warehouse_transfer",
            reference_id=
                payload.reference_id,
            notes=
                movement_notes,
            created_by_id=
                current_user.id,
        )

        in_movement = StockMovement(
            company_id=
                company.id,
            branch_id=(
                destination_warehouse
                .branch_id
            ),
            warehouse_id=(
                destination_warehouse.id
            ),
            product_id=
                product.id,
            serial_number_id=
                serial.id,
            movement_type=(
                StockMovementType
                .TRANSFER_IN.value
            ),
            quantity=
                Decimal("1.000"),
            unit_cost=
                source_average_cost,
            reference_type=
                "warehouse_transfer",
            reference_id=
                payload.reference_id,
            notes=
                movement_notes,
            created_by_id=
                current_user.id,
        )

        session.add(
            out_movement
        )

        session.add(
            in_movement
        )

        out_movements.append(
            out_movement
        )

        in_movements.append(
            in_movement
        )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "inventory."
                "stock_transferred_serialized"
            ),
            module="inventory",
            entity_type=
                "stock_transfer",
            entity_id=(
                out_movements[0].id
                if out_movements
                else None
            ),
            entity_reference=
                payload.reference_id,
            description=(
                "Serialized inventory "
                "transferred between warehouses"
            ),
            before_data={
                "source":
                    before_source,
                "destination":
                    before_destination,
                "serials":
                    serials_before,
            },
            after_data={
                "source":
                    _stock_item_transfer_snapshot(
                        source_stock
                    ),
                "destination":
                    _stock_item_transfer_snapshot(
                        destination_stock
                    ),
                "serials": [
                    {
                        "id":
                            serial.id,
                        "serial_number":
                            serial.serial_number,
                        "warehouse_id":
                            serial.warehouse_id,
                        "status":
                            serial.status,
                    }
                    for serial
                    in serial_records
                ],
            },
            metadata={
                "product_id":
                    product.id,
                "source_warehouse_id":
                    source_warehouse.id,
                "destination_warehouse_id":
                    destination_warehouse.id,
                "serial_number_ids":
                    serial_ids,
                "quantity":
                    quantity,
            },
        )

        await session.commit()

        await session.refresh(
            source_stock
        )

        await session.refresh(
            destination_stock
        )

        for serial in serial_records:
            await session.refresh(
                serial
            )

        for movement in (
            out_movements
            + in_movements
        ):
            await session.refresh(
                movement
            )

    except Exception:
        await session.rollback()
        raise

    return {
        "message":
            "Serialized warehouse transfer completed",
        "product_id":
            product.id,
        "source_warehouse_id":
            source_warehouse.id,
        "destination_warehouse_id":
            destination_warehouse.id,
        "quantity_transferred":
            quantity,
        "source_quantity_on_hand":
            Decimal(
                source_stock
                .quantity_on_hand
            ),
        "destination_quantity_on_hand":
            Decimal(
                destination_stock
                .quantity_on_hand
            ),
        "serials":
            serial_records,
        "transfer_out_movements":
            out_movements,
        "transfer_in_movements":
            in_movements,
    }
