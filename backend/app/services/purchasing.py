from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Branch,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptSerial,
    Product,
    ProductSerialNumber,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    StockItem,
    StockMovement,
    StockMovementType,
    Supplier,
    SupplierInvoice,
    SupplierInvoiceStatus,
    SupplierPayment,
    SupplierPaymentStatus,
    User,
    Warehouse,
)
from app.schemas.purchasing import (
    GoodsReceiptCreate,
    GoodsReceiptItemResponse,
    GoodsReceiptListResponse,
    GoodsReceiptResponse,
    GoodsReceiptSerialResponse,
    SupplierInvoiceCreate,
    SupplierInvoiceListResponse,
    SupplierInvoiceResponse,
    SupplierInvoiceReverseRequest,
    SupplierPaymentCreate,
    SupplierPaymentListResponse,
    SupplierPaymentResponse,
    SupplierPaymentReverseRequest,
    PurchaseOrderCancelRequest,
    PurchaseOrderCreate,
    PurchaseOrderDetailResponse,
    PurchaseOrderItemInput,
    PurchaseOrderItemResponse,
    PurchaseOrderListResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.services.audit import create_audit_log
from app.services.inventory import (
    get_active_company,
)


MONEY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.001")


def money(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        MONEY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def quantity(
    value: Decimal | int | str,
) -> Decimal:
    return Decimal(str(value)).quantize(
        QUANTITY_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def purchase_order_snapshot(
    purchase_order: PurchaseOrder,
) -> dict:
    return {
        "id":
            purchase_order.id,

        "purchase_order_number":
            purchase_order.purchase_order_number,

        "company_id":
            purchase_order.company_id,

        "branch_id":
            purchase_order.branch_id,

        "supplier_id":
            purchase_order.supplier_id,

        "warehouse_id":
            purchase_order.warehouse_id,

        "status":
            purchase_order.status,

        "order_date":
            purchase_order.order_date,

        "expected_date":
            purchase_order.expected_date,

        "subtotal":
            money(
                purchase_order.subtotal
            ),

        "discount_amount":
            money(
                purchase_order
                .discount_amount
            ),

        "tax_amount":
            money(
                purchase_order.tax_amount
            ),

        "grand_total":
            money(
                purchase_order.grand_total
            ),

        "notes":
            purchase_order.notes,

        "approved_by_id":
            purchase_order.approved_by_id,

        "approved_at":
            purchase_order.approved_at,

        "cancelled_by_id":
            purchase_order.cancelled_by_id,

        "cancelled_at":
            purchase_order.cancelled_at,

        "cancellation_reason":
            purchase_order
            .cancellation_reason,

        "items": [
            {
                "id":
                    item.id,

                "product_id":
                    item.product_id,

                "quantity":
                    quantity(
                        item.quantity
                    ),

                "received_quantity":
                    quantity(
                        item.received_quantity
                    ),

                "unit_cost":
                    money(
                        item.unit_cost
                    ),

                "discount_amount":
                    money(
                        item.discount_amount
                    ),

                "tax_amount":
                    money(
                        item.tax_amount
                    ),

                "line_total":
                    money(
                        item.line_total
                    ),

                "notes":
                    item.notes,
            }
            for item
            in purchase_order.items
        ],
    }


def validate_dates(
    *,
    order_date,
    expected_date,
) -> None:
    if (
        expected_date is not None
        and expected_date < order_date
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Expected delivery date cannot "
                "be earlier than order date"
            ),
        )


async def get_supplier_for_company(
    session: AsyncSession,
    *,
    company_id: int,
    supplier_id: int,
) -> Supplier:
    result = await session.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == company_id,
        )
    )

    supplier = result.scalar_one_or_none()

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier was not found",
        )

    if not supplier.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Supplier is inactive",
        )

    return supplier


async def get_warehouse_for_company(
    session: AsyncSession,
    *,
    company_id: int,
    warehouse_id: int,
) -> Warehouse:
    result = await session.execute(
        select(Warehouse, Branch)
        .join(
            Branch,
            Branch.id == Warehouse.branch_id,
        )
        .where(
            Warehouse.id == warehouse_id,
            Branch.company_id == company_id,
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse was not found",
        )

    warehouse, _branch = row

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse is inactive",
        )

    return warehouse


async def get_product_for_company(
    session: AsyncSession,
    *,
    company_id: int,
    product_id: int,
) -> Product:
    result = await session.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == company_id,
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product was not found",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Product is inactive: "
                f"{product.name}"
            ),
        )

    return product


async def get_purchase_order_or_404(
    session: AsyncSession,
    *,
    company_id: int,
    purchase_order_id: int,
    for_update: bool = False,
) -> PurchaseOrder:
    statement = (
        select(PurchaseOrder)
        .options(
            selectinload(
                PurchaseOrder.items
            )
        )
        .where(
            PurchaseOrder.id
            == purchase_order_id,
            PurchaseOrder.company_id
            == company_id,
        )
    )

    if for_update:
        statement = statement.with_for_update()

    result = await session.execute(
        statement
    )

    purchase_order = (
        result.scalar_one_or_none()
    )

    if purchase_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order was not found",
        )

    return purchase_order


async def build_item(
    session: AsyncSession,
    *,
    company_id: int,
    item_input: PurchaseOrderItemInput,
) -> tuple[
    PurchaseOrderItem,
    Product,
]:
    product = await get_product_for_company(
        session,
        company_id=company_id,
        product_id=item_input.product_id,
    )

    item_quantity = quantity(
        item_input.quantity
    )

    unit_cost = money(
        item_input.unit_cost
    )

    discount = money(
        item_input.discount_amount
    )

    tax = money(
        item_input.tax_amount
    )

    gross = money(
        item_quantity * unit_cost
    )

    if discount > gross:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Item discount cannot exceed "
                f"gross amount for product "
                f"{product.name}"
            ),
        )

    line_total = money(
        gross
        - discount
        + tax
    )

    item = PurchaseOrderItem(
        product_id=product.id,
        quantity=item_quantity,
        received_quantity=Decimal(
            "0.000"
        ),
        unit_cost=unit_cost,
        discount_amount=discount,
        tax_amount=tax,
        line_total=line_total,
        notes=item_input.notes,
    )

    return item, product


def recalculate_totals(
    purchase_order: PurchaseOrder,
) -> None:
    subtotal = Decimal("0.00")
    discount = Decimal("0.00")
    tax = Decimal("0.00")

    for item in purchase_order.items:
        subtotal += money(
            quantity(item.quantity)
            * money(item.unit_cost)
        )

        discount += money(
            item.discount_amount
        )

        tax += money(
            item.tax_amount
        )

    purchase_order.subtotal = money(
        subtotal
    )

    purchase_order.discount_amount = money(
        discount
    )

    purchase_order.tax_amount = money(
        tax
    )

    purchase_order.grand_total = money(
        subtotal
        - discount
        + tax
    )


async def replace_items(
    session: AsyncSession,
    *,
    purchase_order: PurchaseOrder,
    company_id: int,
    item_inputs: list[
        PurchaseOrderItemInput
    ],
) -> None:
    product_ids = [
        item.product_id
        for item in item_inputs
    ]

    if (
        len(product_ids)
        != len(set(product_ids))
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "A product can appear only once "
                "on a purchase order"
            ),
        )

    purchase_order.items.clear()

    for item_input in item_inputs:
        item, _product = await build_item(
            session,
            company_id=company_id,
            item_input=item_input,
        )

        purchase_order.items.append(
            item
        )

    recalculate_totals(
        purchase_order
    )


async def build_purchase_order_response(
    session: AsyncSession,
    purchase_order: PurchaseOrder,
) -> PurchaseOrderDetailResponse:
    supplier_result = await session.execute(
        select(Supplier).where(
            Supplier.id
            == purchase_order.supplier_id
        )
    )

    supplier = (
        supplier_result.scalar_one()
    )

    warehouse_result = (
        await session.execute(
            select(Warehouse).where(
                Warehouse.id
                == purchase_order.warehouse_id
            )
        )
    )

    warehouse = (
        warehouse_result.scalar_one()
    )

    product_ids = {
        item.product_id
        for item in purchase_order.items
    }

    products = {}

    if product_ids:
        product_result = await session.execute(
            select(Product).where(
                Product.id.in_(
                    product_ids
                )
            )
        )

        products = {
            product.id: product
            for product
            in product_result.scalars().all()
        }

    if (
        purchase_order
        .purchase_order_number
        is None
    ):
        raise RuntimeError(
            "Purchase order number "
            "has not been assigned"
        )

    return PurchaseOrderDetailResponse(
        id=purchase_order.id,

        purchase_order_number=(
            purchase_order
            .purchase_order_number
        ),

        company_id=(
            purchase_order.company_id
        ),

        branch_id=(
            purchase_order.branch_id
        ),

        supplier_id=(
            purchase_order.supplier_id
        ),

        supplier_code=(
            supplier.supplier_code
        ),

        supplier_name=(
            supplier.company_name
        ),

        warehouse_id=(
            purchase_order.warehouse_id
        ),

        warehouse_code=warehouse.code,

        warehouse_name=warehouse.name,

        status=purchase_order.status,

        order_date=(
            purchase_order.order_date
        ),

        expected_date=(
            purchase_order.expected_date
        ),

        subtotal=money(
            purchase_order.subtotal
        ),

        discount_amount=money(
            purchase_order
            .discount_amount
        ),

        tax_amount=money(
            purchase_order.tax_amount
        ),

        grand_total=money(
            purchase_order.grand_total
        ),

        notes=purchase_order.notes,

        approved_by_id=(
            purchase_order.approved_by_id
        ),

        approved_at=(
            purchase_order.approved_at
        ),

        cancelled_by_id=(
            purchase_order.cancelled_by_id
        ),

        cancelled_at=(
            purchase_order.cancelled_at
        ),

        cancellation_reason=(
            purchase_order
            .cancellation_reason
        ),

        created_by_id=(
            purchase_order.created_by_id
        ),

        updated_by_id=(
            purchase_order.updated_by_id
        ),

        created_at=(
            purchase_order.created_at
        ),

        updated_at=(
            purchase_order.updated_at
        ),

        items=[
            PurchaseOrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_code=(
                    products[
                        item.product_id
                    ].product_code
                    if item.product_id
                    in products
                    else None
                ),
                product_name=(
                    products[
                        item.product_id
                    ].name
                    if item.product_id
                    in products
                    else (
                        f"Product "
                        f"{item.product_id}"
                    )
                ),
                quantity=quantity(
                    item.quantity
                ),
                received_quantity=quantity(
                    item.received_quantity
                ),
                unit_cost=money(
                    item.unit_cost
                ),
                discount_amount=money(
                    item.discount_amount
                ),
                tax_amount=money(
                    item.tax_amount
                ),
                line_total=money(
                    item.line_total
                ),
                notes=item.notes,
            )
            for item
            in purchase_order.items
        ],
    )


async def create_purchase_order(
    session: AsyncSession,
    *,
    payload: PurchaseOrderCreate,
    current_user: User,
) -> PurchaseOrderDetailResponse:
    company = await get_active_company(
        session
    )

    supplier = await get_supplier_for_company(
        session,
        company_id=company.id,
        supplier_id=payload.supplier_id,
    )

    warehouse = await get_warehouse_for_company(
        session,
        company_id=company.id,
        warehouse_id=payload.warehouse_id,
    )

    validate_dates(
        order_date=payload.order_date,
        expected_date=payload.expected_date,
    )

    purchase_order = PurchaseOrder(
        company_id=company.id,
        branch_id=warehouse.branch_id,
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        purchase_order_number=None,
        status=(
            PurchaseOrderStatus.DRAFT.value
        ),
        order_date=payload.order_date,
        expected_date=payload.expected_date,
        notes=payload.notes,
        subtotal=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        created_by_id=current_user.id,
        updated_by_id=None,
    items=[],
    )

    session.add(purchase_order)

    try:
        await replace_items(
            session,
            purchase_order=purchase_order,
            company_id=company.id,
            item_inputs=payload.items,
        )

        await session.flush()

        purchase_order.purchase_order_number = (
            f"PO-{purchase_order.id:06d}"
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "purchase_order_created"
            ),
            module="purchasing",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            entity_reference=(
                purchase_order
                .purchase_order_number
            ),
            description=(
                "Purchase order draft created"
            ),
            before_data=None,
            after_data=(
                purchase_order_snapshot(
                    purchase_order
                )
            ),
            metadata={
                "supplier_id":
                    supplier.id,

                "warehouse_id":
                    warehouse.id,

                "item_count":
                    len(
                        purchase_order.items
                    ),

                "grand_total":
                    purchase_order
                    .grand_total,
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Purchase order could not "
                "be created because a unique "
                "value already exists"
            ),
        ) from exc

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order.id
            ),
        )
    )

    return (
        await build_purchase_order_response(
            session,
            purchase_order,
        )
    )


async def list_purchase_orders(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    order_status: PurchaseOrderStatus | None,
    supplier_id: int | None,
    warehouse_id: int | None,
) -> PurchaseOrderListResponse:
    company = await get_active_company(
        session
    )

    filters = [
        PurchaseOrder.company_id
        == company.id,
    ]

    if order_status is not None:
        filters.append(
            PurchaseOrder.status
            == order_status.value
        )

    if supplier_id is not None:
        filters.append(
            PurchaseOrder.supplier_id
            == supplier_id
        )

    if warehouse_id is not None:
        filters.append(
            PurchaseOrder.warehouse_id
            == warehouse_id
        )

    if search and search.strip():
        pattern = (
            f"%{search.strip()}%"
        )

        filters.append(
            or_(
                PurchaseOrder
                .purchase_order_number
                .ilike(pattern),

                PurchaseOrder.notes.ilike(
                    pattern
                ),

                Supplier
                .company_name
                .ilike(pattern),

                Supplier
                .supplier_code
                .ilike(pattern),
            )
        )

    count_statement = (
        select(
            func.count(
                PurchaseOrder.id
            )
        )
        .join(
            Supplier,
            Supplier.id
            == PurchaseOrder.supplier_id,
        )
        .where(*filters)
    )

    total = int(
        (
            await session.execute(
                count_statement
            )
        ).scalar_one()
    )

    statement = (
        select(
            PurchaseOrder,
            Supplier,
            Warehouse,
        )
        .join(
            Supplier,
            Supplier.id
            == PurchaseOrder.supplier_id,
        )
        .join(
            Warehouse,
            Warehouse.id
            == PurchaseOrder.warehouse_id,
        )
        .where(*filters)
        .order_by(
            PurchaseOrder.id.desc()
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    result = await session.execute(
        statement
    )

    items = []

    for (
        purchase_order,
        supplier,
        warehouse,
    ) in result.all():
        if (
            purchase_order
            .purchase_order_number
            is None
        ):
            continue

        items.append(
            PurchaseOrderResponse(
                id=purchase_order.id,

                purchase_order_number=(
                    purchase_order
                    .purchase_order_number
                ),

                company_id=(
                    purchase_order
                    .company_id
                ),

                branch_id=(
                    purchase_order
                    .branch_id
                ),

                supplier_id=(
                    purchase_order
                    .supplier_id
                ),

                supplier_code=(
                    supplier.supplier_code
                ),

                supplier_name=(
                    supplier.company_name
                ),

                warehouse_id=(
                    warehouse.id
                ),

                warehouse_code=(
                    warehouse.code
                ),

                warehouse_name=(
                    warehouse.name
                ),

                status=(
                    purchase_order.status
                ),

                order_date=(
                    purchase_order
                    .order_date
                ),

                expected_date=(
                    purchase_order
                    .expected_date
                ),

                subtotal=money(
                    purchase_order.subtotal
                ),

                discount_amount=money(
                    purchase_order
                    .discount_amount
                ),

                tax_amount=money(
                    purchase_order
                    .tax_amount
                ),

                grand_total=money(
                    purchase_order
                    .grand_total
                ),

                notes=(
                    purchase_order.notes
                ),

                approved_by_id=(
                    purchase_order
                    .approved_by_id
                ),

                approved_at=(
                    purchase_order
                    .approved_at
                ),

                cancelled_by_id=(
                    purchase_order
                    .cancelled_by_id
                ),

                cancelled_at=(
                    purchase_order
                    .cancelled_at
                ),

                cancellation_reason=(
                    purchase_order
                    .cancellation_reason
                ),

                created_by_id=(
                    purchase_order
                    .created_by_id
                ),

                updated_by_id=(
                    purchase_order
                    .updated_by_id
                ),

                created_at=(
                    purchase_order
                    .created_at
                ),

                updated_at=(
                    purchase_order
                    .updated_at
                ),
            )
        )

    return PurchaseOrderListResponse(
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


async def get_purchase_order(
    session: AsyncSession,
    *,
    purchase_order_id: int,
) -> PurchaseOrderDetailResponse:
    company = await get_active_company(
        session
    )

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order_id
            ),
        )
    )

    return (
        await build_purchase_order_response(
            session,
            purchase_order,
        )
    )


async def update_purchase_order(
    session: AsyncSession,
    *,
    purchase_order_id: int,
    payload: PurchaseOrderUpdate,
    current_user: User,
) -> PurchaseOrderDetailResponse:
    company = await get_active_company(
        session
    )

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order_id
            ),
            for_update=True,
        )
    )

    if (
        purchase_order.status
        != PurchaseOrderStatus.DRAFT.value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Only draft purchase orders "
                "can be edited"
            ),
        )

    before = purchase_order_snapshot(
        purchase_order
    )

    values = payload.model_dump(
        exclude_unset=True
    )

    supplier_id = values.get(
        "supplier_id",
        purchase_order.supplier_id,
    )

    warehouse_id = values.get(
        "warehouse_id",
        purchase_order.warehouse_id,
    )

    supplier = await get_supplier_for_company(
        session,
        company_id=company.id,
        supplier_id=supplier_id,
    )

    warehouse = await get_warehouse_for_company(
        session,
        company_id=company.id,
        warehouse_id=warehouse_id,
    )

    new_order_date = values.get(
        "order_date",
        purchase_order.order_date,
    )

    new_expected_date = (
        values["expected_date"]
        if "expected_date" in values
        else purchase_order.expected_date
    )

    validate_dates(
        order_date=new_order_date,
        expected_date=new_expected_date,
    )

    purchase_order.supplier_id = (
        supplier.id
    )

    purchase_order.warehouse_id = (
        warehouse.id
    )

    purchase_order.branch_id = (
        warehouse.branch_id
    )

    purchase_order.order_date = (
        new_order_date
    )

    purchase_order.expected_date = (
        new_expected_date
    )

    if "notes" in values:
        purchase_order.notes = (
            values["notes"]
        )

    if payload.items is not None:
        await replace_items(
            session,
            purchase_order=purchase_order,
            company_id=company.id,
            item_inputs=payload.items,
        )

    purchase_order.updated_by_id = (
        current_user.id
    )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "purchase_order_updated"
            ),
            module="purchasing",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            entity_reference=(
                purchase_order
                .purchase_order_number
            ),
            description=(
                "Purchase order draft updated"
            ),
            before_data=before,
            after_data=(
                purchase_order_snapshot(
                    purchase_order
                )
            ),
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Purchase order could not "
                "be updated"
            ),
        ) from exc

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order.id
            ),
        )
    )

    return (
        await build_purchase_order_response(
            session,
            purchase_order,
        )
    )


async def approve_purchase_order(
    session: AsyncSession,
    *,
    purchase_order_id: int,
    current_user: User,
) -> PurchaseOrderDetailResponse:
    company = await get_active_company(
        session
    )

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order_id
            ),
            for_update=True,
        )
    )

    if (
        purchase_order.status
        != PurchaseOrderStatus.DRAFT.value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Only draft purchase orders "
                "can be approved"
            ),
        )

    if not purchase_order.items:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Purchase order has no items"
            ),
        )

    before = purchase_order_snapshot(
        purchase_order
    )

    now = datetime.now(
        timezone.utc
    )

    purchase_order.status = (
        PurchaseOrderStatus
        .APPROVED
        .value
    )

    purchase_order.approved_by_id = (
        current_user.id
    )

    purchase_order.approved_at = now

    purchase_order.updated_by_id = (
        current_user.id
    )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "purchase_order_approved"
            ),
            module="purchasing",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            entity_reference=(
                purchase_order
                .purchase_order_number
            ),
            description=(
                "Purchase order approved"
            ),
            before_data=before,
            after_data=(
                purchase_order_snapshot(
                    purchase_order
                )
            ),
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order.id
            ),
        )
    )

    return (
        await build_purchase_order_response(
            session,
            purchase_order,
        )
    )


async def cancel_purchase_order(
    session: AsyncSession,
    *,
    purchase_order_id: int,
    payload: PurchaseOrderCancelRequest,
    current_user: User,
) -> PurchaseOrderDetailResponse:
    company = await get_active_company(
        session
    )

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order_id
            ),
            for_update=True,
        )
    )

    allowed = {
        PurchaseOrderStatus.DRAFT.value,
        PurchaseOrderStatus.APPROVED.value,
    }

    if purchase_order.status not in allowed:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Purchase order cannot be "
                "cancelled in its current state"
            ),
        )

    before = purchase_order_snapshot(
        purchase_order
    )

    now = datetime.now(
        timezone.utc
    )

    purchase_order.status = (
        PurchaseOrderStatus
        .CANCELLED
        .value
    )

    purchase_order.cancelled_by_id = (
        current_user.id
    )

    purchase_order.cancelled_at = now

    purchase_order.cancellation_reason = (
        payload.reason.strip()
    )

    purchase_order.updated_by_id = (
        current_user.id
    )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "purchase_order_cancelled"
            ),
            module="purchasing",
            entity_type="purchase_order",
            entity_id=purchase_order.id,
            entity_reference=(
                purchase_order
                .purchase_order_number
            ),
            description=(
                "Purchase order cancelled"
            ),
            before_data=before,
            after_data=(
                purchase_order_snapshot(
                    purchase_order
                )
            ),
            metadata={
                "reason":
                    payload.reason.strip(),
            },
        )

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order.id
            ),
        )
    )

    return (
        await build_purchase_order_response(
            session,
            purchase_order,
        )
    )


async def _get_stock_item_for_update(
    session: AsyncSession,
    *,
    warehouse_id: int,
    product_id: int,
) -> StockItem | None:
    result = await session.execute(
        select(StockItem)
        .where(
            StockItem.warehouse_id
            == warehouse_id,
            StockItem.product_id
            == product_id,
        )
        .with_for_update()
    )

    return result.scalar_one_or_none()


def _weighted_average_cost(
    *,
    old_quantity: Decimal,
    old_average_cost: Decimal,
    received_quantity: Decimal,
    received_cost: Decimal,
) -> Decimal:
    old_quantity = quantity(
        old_quantity
    )

    received_quantity = quantity(
        received_quantity
    )

    new_quantity = (
        old_quantity
        + received_quantity
    )

    if new_quantity <= Decimal(
        "0.000"
    ):
        return money(
            received_cost
        )

    old_value = (
        old_quantity
        * money(old_average_cost)
    )

    received_value = (
        received_quantity
        * money(received_cost)
    )

    return money(
        (
            old_value
            + received_value
        )
        / new_quantity
    )


async def _increase_stock(
    session: AsyncSession,
    *,
    purchase_order: PurchaseOrder,
    product: Product,
    received_quantity: Decimal,
    unit_cost: Decimal,
) -> StockItem:
    stock_item = (
        await _get_stock_item_for_update(
            session,
            warehouse_id=(
                purchase_order.warehouse_id
            ),
            product_id=product.id,
        )
    )

    received_quantity = quantity(
        received_quantity
    )

    unit_cost = money(
        unit_cost
    )

    if stock_item is None:
        stock_item = StockItem(
            warehouse_id=(
                purchase_order.warehouse_id
            ),
            product_id=product.id,
            quantity_on_hand=Decimal(
                "0.000"
            ),
            quantity_reserved=Decimal(
                "0.000"
            ),
            average_cost=Decimal(
                "0.00"
            ),
        )

        session.add(stock_item)

        await session.flush()

    old_quantity = quantity(
        stock_item.quantity_on_hand
    )

    stock_item.average_cost = (
        _weighted_average_cost(
            old_quantity=old_quantity,
            old_average_cost=(
                stock_item.average_cost
            ),
            received_quantity=(
                received_quantity
            ),
            received_cost=unit_cost,
        )
    )

    stock_item.quantity_on_hand = (
        old_quantity
        + received_quantity
    )

    await session.flush()

    return stock_item


async def _create_purchase_receipt_movement(
    session: AsyncSession,
    *,
    purchase_order: PurchaseOrder,
    product: Product,
    received_quantity: Decimal,
    unit_cost: Decimal,
    grn_number: str,
    current_user: User,
    serial_number_id: int | None = None,
    notes: str | None = None,
) -> StockMovement:
    movement = StockMovement(
        company_id=(
            purchase_order.company_id
        ),
        branch_id=(
            purchase_order.branch_id
        ),
        warehouse_id=(
            purchase_order.warehouse_id
        ),
        product_id=product.id,
        serial_number_id=(
            serial_number_id
        ),
        movement_type=(
            StockMovementType
            .PURCHASE_RECEIPT
            .value
        ),
        quantity=quantity(
            received_quantity
        ),
        unit_cost=money(
            unit_cost
        ),
        reference_type=(
            "goods_receipt"
        ),
        reference_id=grn_number,
        notes=notes,
        created_by_id=current_user.id,
    )

    session.add(movement)

    await session.flush()

    return movement


async def _create_received_serial(
    session: AsyncSession,
    *,
    purchase_order: PurchaseOrder,
    product: Product,
    serial_number: str,
    secondary_serial_number: str | None,
    current_user: User,
    received_at: datetime,
) -> ProductSerialNumber:
    serial_number = (
        serial_number.strip()
    )

    secondary = (
        secondary_serial_number.strip()
        if secondary_serial_number
        else None
    )

    duplicate_result = (
        await session.execute(
            select(
                ProductSerialNumber.id
            ).where(
                ProductSerialNumber.company_id
                == purchase_order.company_id,
                ProductSerialNumber.serial_number
                == serial_number,
            )
        )
    )

    if (
        duplicate_result.scalar_one_or_none()
        is not None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Serial number already exists: "
                f"{serial_number}"
            ),
        )

    serial = ProductSerialNumber(
        company_id=(
            purchase_order.company_id
        ),
        product_id=product.id,
        serial_number=serial_number,
        secondary_serial_number=secondary,
        warehouse_id=(
            purchase_order.warehouse_id
        ),
        supplier_id=(
            purchase_order.supplier_id
        ),
        status="available",
        current_customer_id=None,
        warranty_start_date=None,
        warranty_end_date=None,
        received_at=received_at,
        sold_at=None,
        notes=(
            "Received through purchase "
            f"order "
            f"{purchase_order.purchase_order_number}"
        ),
        created_by_id=current_user.id,
    )

    session.add(serial)

    await session.flush()

    return serial


async def _get_goods_receipt_or_404(
    session: AsyncSession,
    *,
    company_id: int,
    goods_receipt_id: int,
) -> GoodsReceipt:
    result = await session.execute(
        select(GoodsReceipt)
        .options(
            selectinload(
                GoodsReceipt.items
            ).selectinload(
                GoodsReceiptItem.serials
            )
        )
        .where(
            GoodsReceipt.id
            == goods_receipt_id,
            GoodsReceipt.company_id
            == company_id,
        )
    )

    receipt = (
        result.scalar_one_or_none()
    )

    if receipt is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Goods receipt was not found"
            ),
        )

    return receipt


async def _build_goods_receipt_response(
    session: AsyncSession,
    *,
    receipt: GoodsReceipt,
) -> GoodsReceiptResponse:
    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=receipt.company_id,
            purchase_order_id=(
                receipt.purchase_order_id
            ),
        )
    )

    supplier_result = (
        await session.execute(
            select(Supplier).where(
                Supplier.id
                == receipt.supplier_id
            )
        )
    )

    supplier = (
        supplier_result.scalar_one()
    )

    warehouse_result = (
        await session.execute(
            select(Warehouse).where(
                Warehouse.id
                == receipt.warehouse_id
            )
        )
    )

    warehouse = (
        warehouse_result.scalar_one()
    )

    product_ids = {
        item.product_id
        for item in receipt.items
    }

    product_result = await session.execute(
        select(Product).where(
            Product.id.in_(
                product_ids
            )
        )
    )

    products = {
        product.id: product
        for product
        in product_result.scalars().all()
    }

    if receipt.grn_number is None:
        raise RuntimeError(
            "GRN number has not been assigned"
        )

    if (
        purchase_order
        .purchase_order_number
        is None
    ):
        raise RuntimeError(
            "Purchase order number missing"
        )

    return GoodsReceiptResponse(
        id=receipt.id,
        grn_number=receipt.grn_number,

        purchase_order_id=(
            receipt.purchase_order_id
        ),

        purchase_order_number=(
            purchase_order
            .purchase_order_number
        ),

        company_id=receipt.company_id,
        branch_id=receipt.branch_id,

        supplier_id=receipt.supplier_id,
        supplier_name=(
            supplier.company_name
        ),

        warehouse_id=(
            receipt.warehouse_id
        ),

        warehouse_code=warehouse.code,
        warehouse_name=warehouse.name,

        received_at=receipt.received_at,

        delivery_note_number=(
            receipt.delivery_note_number
        ),

        notes=receipt.notes,

        received_by_id=(
            receipt.received_by_id
        ),

        po_status=(
            purchase_order.status
        ),

        items=[
            GoodsReceiptItemResponse(
                id=item.id,

                purchase_order_item_id=(
                    item
                    .purchase_order_item_id
                ),

                product_id=item.product_id,

                product_code=(
                    products[
                        item.product_id
                    ].product_code
                ),

                product_name=(
                    products[
                        item.product_id
                    ].name
                ),

                quantity_received=quantity(
                    item.quantity_received
                ),

                unit_cost=money(
                    item.unit_cost
                ),

                serials=[
                    GoodsReceiptSerialResponse(
                        id=serial.id,

                        product_serial_number_id=(
                            serial
                            .product_serial_number_id
                        ),

                        serial_number=(
                            serial.serial_number
                        ),

                        secondary_serial_number=(
                            serial
                            .secondary_serial_number
                        ),
                    )
                    for serial
                    in item.serials
                ],
            )
            for item
            in receipt.items
        ],

        created_at=receipt.created_at,
    )


async def receive_purchase_order(
    session: AsyncSession,
    *,
    purchase_order_id: int,
    payload: GoodsReceiptCreate,
    current_user: User,
) -> GoodsReceiptResponse:
    company = await get_active_company(
        session
    )

    purchase_order = (
        await get_purchase_order_or_404(
            session,
            company_id=company.id,
            purchase_order_id=(
                purchase_order_id
            ),
            for_update=True,
        )
    )

    allowed_statuses = {
        PurchaseOrderStatus
        .APPROVED
        .value,

        PurchaseOrderStatus
        .ORDERED
        .value,

        PurchaseOrderStatus
        .PARTIALLY_RECEIVED
        .value,
    }

    if (
        purchase_order.status
        not in allowed_statuses
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Purchase order cannot be "
                "received in its current state"
            ),
        )

    request_item_ids = [
        item.purchase_order_item_id
        for item in payload.items
    ]

    if (
        len(request_item_ids)
        != len(set(request_item_ids))
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "A purchase order item can "
                "appear only once per goods "
                "receipt"
            ),
        )

    po_items = {
        item.id: item
        for item in purchase_order.items
    }

    before = purchase_order_snapshot(
        purchase_order
    )

    now = datetime.now(
        timezone.utc
    )

    receipt = GoodsReceipt(
        company_id=(
            purchase_order.company_id
        ),
        branch_id=(
            purchase_order.branch_id
        ),
        purchase_order_id=(
            purchase_order.id
        ),
        supplier_id=(
            purchase_order.supplier_id
        ),
        warehouse_id=(
            purchase_order.warehouse_id
        ),
        grn_number=None,
        delivery_note_number=(
            payload.delivery_note_number
        ),
        received_at=now,
        notes=payload.notes,
        received_by_id=current_user.id,
        items=[],
    )

    session.add(receipt)

    try:
        await session.flush()

        receipt.grn_number = (
            f"GRN-{receipt.id:06d}"
        )

        await session.flush()

        for request_item in payload.items:
            po_item = po_items.get(
                request_item
                .purchase_order_item_id
            )

            if po_item is None:
                raise HTTPException(
                    status_code=(
                        status.HTTP_422_UNPROCESSABLE_ENTITY
                    ),
                    detail=(
                        "Purchase order item does "
                        "not belong to this purchase "
                        "order"
                    ),
                )

            receive_quantity = quantity(
                request_item.quantity
            )

            ordered_quantity = quantity(
                po_item.quantity
            )

            already_received = quantity(
                po_item.received_quantity
            )

            remaining = (
                ordered_quantity
                - already_received
            )

            if (
                receive_quantity
                > remaining
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Receipt quantity exceeds "
                        "the remaining purchase "
                        "order quantity"
                    ),
                )

            product = (
                await get_product_for_company(
                    session,
                    company_id=company.id,
                    product_id=(
                        po_item.product_id
                    ),
                )
            )

            is_serialized = bool(
                product.track_serial_numbers
            )

            if is_serialized:
                if (
                    receive_quantity
                    != receive_quantity
                    .to_integral_value()
                ):
                    raise HTTPException(
                        status_code=(
                            status.HTTP_422_UNPROCESSABLE_ENTITY
                        ),
                        detail=(
                            "Serialized product "
                            "quantity must be a "
                            "whole number"
                        ),
                    )

                expected_serial_count = int(
                    receive_quantity
                )

                if (
                    len(
                        request_item.serials
                    )
                    != expected_serial_count
                ):
                    raise HTTPException(
                        status_code=(
                            status.HTTP_422_UNPROCESSABLE_ENTITY
                        ),
                        detail=(
                            "Serialized receipt "
                            "quantity must match "
                            "the serial number count"
                        ),
                    )

                normalized_serials = [
                    serial.serial_number
                    .strip()
                    for serial
                    in request_item.serials
                ]

                if (
                    len(normalized_serials)
                    != len(
                        set(
                            normalized_serials
                        )
                    )
                ):
                    raise HTTPException(
                        status_code=(
                            status.HTTP_422_UNPROCESSABLE_ENTITY
                        ),
                        detail=(
                            "Duplicate serial "
                            "numbers were supplied"
                        ),
                    )

            elif request_item.serials:
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Serial numbers cannot "
                        "be supplied for a "
                        "non-serialized product"
                    ),
                )

            receipt_item = (
                GoodsReceiptItem(
                    purchase_order_item_id=(
                        po_item.id
                    ),
                    product_id=(
                        product.id
                    ),
                    quantity_received=(
                        receive_quantity
                    ),
                    unit_cost=money(
                        po_item.unit_cost
                    ),
                    serials=[],
                )
            )

            receipt.items.append(
                receipt_item
            )

            await session.flush()

            await _increase_stock(
                session,
                purchase_order=(
                    purchase_order
                ),
                product=product,
                received_quantity=(
                    receive_quantity
                ),
                unit_cost=(
                    po_item.unit_cost
                ),
            )

            if is_serialized:
                for serial_input in (
                    request_item.serials
                ):
                    serial = (
                        await _create_received_serial(
                            session,
                            purchase_order=(
                                purchase_order
                            ),
                            product=product,
                            serial_number=(
                                serial_input
                                .serial_number
                            ),
                            secondary_serial_number=(
                                serial_input
                                .secondary_serial_number
                            ),
                            current_user=(
                                current_user
                            ),
                            received_at=now,
                        )
                    )

                    receipt_serial = (
                        GoodsReceiptSerial(
                            product_serial_number_id=(
                                serial.id
                            ),
                            serial_number=(
                                serial.serial_number
                            ),
                            secondary_serial_number=(
                                serial
                                .secondary_serial_number
                            ),
                        )
                    )

                    receipt_item.serials.append(
                        receipt_serial
                    )

                    await _create_purchase_receipt_movement(
                        session,
                        purchase_order=(
                            purchase_order
                        ),
                        product=product,
                        received_quantity=Decimal(
                            "1.000"
                        ),
                        unit_cost=(
                            po_item.unit_cost
                        ),
                        grn_number=(
                            receipt.grn_number
                        ),
                        current_user=(
                            current_user
                        ),
                        serial_number_id=(
                            serial.id
                        ),
                        notes=(
                            "Serialized purchase "
                            "receipt"
                        ),
                    )

            else:
                await _create_purchase_receipt_movement(
                    session,
                    purchase_order=(
                        purchase_order
                    ),
                    product=product,
                    received_quantity=(
                        receive_quantity
                    ),
                    unit_cost=(
                        po_item.unit_cost
                    ),
                    grn_number=(
                        receipt.grn_number
                    ),
                    current_user=(
                        current_user
                    ),
                    notes=(
                        "Non-serialized purchase "
                        "receipt"
                    ),
                )

            po_item.received_quantity = (
                already_received
                + receive_quantity
            )

        all_complete = all(
            quantity(item.received_quantity)
            >= quantity(item.quantity)
            for item
            in purchase_order.items
        )

        any_received = any(
            quantity(item.received_quantity)
            > Decimal("0.000")
            for item
            in purchase_order.items
        )

        if all_complete:
            purchase_order.status = (
                PurchaseOrderStatus
                .RECEIVED
                .value
            )

        elif any_received:
            purchase_order.status = (
                PurchaseOrderStatus
                .PARTIALLY_RECEIVED
                .value
            )

        purchase_order.updated_by_id = (
            current_user.id
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "goods_receipt_created"
            ),
            module="purchasing",
            entity_type="goods_receipt",
            entity_id=receipt.id,
            entity_reference=(
                receipt.grn_number
            ),
            description=(
                "Goods received against "
                "purchase order"
            ),
            before_data=before,
            after_data=(
                purchase_order_snapshot(
                    purchase_order
                )
            ),
            metadata={
                "purchase_order_id":
                    purchase_order.id,

                "purchase_order_number":
                    purchase_order
                    .purchase_order_number,

                "grn_number":
                    receipt.grn_number,

                "warehouse_id":
                    purchase_order
                    .warehouse_id,

                "supplier_id":
                    purchase_order
                    .supplier_id,

                "item_count":
                    len(
                        receipt.items
                    ),
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Goods receipt conflicts "
                "with an existing record"
            ),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    receipt = (
        await _get_goods_receipt_or_404(
            session,
            company_id=company.id,
            goods_receipt_id=receipt.id,
        )
    )

    return await _build_goods_receipt_response(
        session,
        receipt=receipt,
    )


async def get_goods_receipt(
    session: AsyncSession,
    *,
    goods_receipt_id: int,
) -> GoodsReceiptResponse:
    company = await get_active_company(
        session
    )

    receipt = (
        await _get_goods_receipt_or_404(
            session,
            company_id=company.id,
            goods_receipt_id=(
                goods_receipt_id
            ),
        )
    )

    return await _build_goods_receipt_response(
        session,
        receipt=receipt,
    )


async def list_goods_receipts(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    purchase_order_id: int | None,
    supplier_id: int | None,
) -> GoodsReceiptListResponse:
    company = await get_active_company(
        session
    )

    filters = [
        GoodsReceipt.company_id
        == company.id,
    ]

    if purchase_order_id is not None:
        filters.append(
            GoodsReceipt.purchase_order_id
            == purchase_order_id
        )

    if supplier_id is not None:
        filters.append(
            GoodsReceipt.supplier_id
            == supplier_id
        )

    total = int(
        (
            await session.execute(
                select(
                    func.count(
                        GoodsReceipt.id
                    )
                ).where(*filters)
            )
        ).scalar_one()
    )

    result = await session.execute(
        select(GoodsReceipt)
        .options(
            selectinload(
                GoodsReceipt.items
            ).selectinload(
                GoodsReceiptItem.serials
            )
        )
        .where(*filters)
        .order_by(
            GoodsReceipt.id.desc()
        )
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
    )

    receipts = result.scalars().all()

    items = [
        await _build_goods_receipt_response(
            session,
            receipt=receipt,
        )
        for receipt
        in receipts
    ]

    return GoodsReceiptListResponse(
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


ALLOWED_SUPPLIER_PAYMENT_METHODS = {
    "cash",
    "card",
    "bank_transfer",
    "cheque",
    "online",
    "other",
}


def supplier_invoice_snapshot(
    invoice: SupplierInvoice,
) -> dict:
    return {
        "id": invoice.id,
        "invoice_number":
            invoice.invoice_number,
        "supplier_id":
            invoice.supplier_id,
        "supplier_invoice_number":
            invoice.supplier_invoice_number,
        "grand_total":
            str(invoice.grand_total),
        "paid_amount":
            str(invoice.paid_amount),
        "balance_amount":
            str(invoice.balance_amount),
        "status":
            invoice.status,
        "is_reversed":
            invoice.is_reversed,
    }


def supplier_payment_snapshot(
    payment: SupplierPayment,
) -> dict:
    return {
        "id": payment.id,
        "payment_number":
            payment.payment_number,
        "supplier_id":
            payment.supplier_id,
        "supplier_invoice_id":
            payment.supplier_invoice_id,
        "amount":
            str(payment.amount),
        "payment_method":
            payment.payment_method,
        "status":
            payment.status,
        "is_reversed":
            payment.is_reversed,
    }


# PHASE3_DEFAULT_BRANCH_RESOLUTION_REPAIR
async def _get_default_branch_for_company(
    session: AsyncSession,
    *,
    company_id: int,
) -> Branch:
    result = await session.execute(
        select(Branch)
        .where(
            Branch.company_id
            == company_id,
            Branch.is_active.is_(True),
        )
        .order_by(
            Branch.is_main_branch.desc(),
            Branch.id.asc(),
        )
    )

    branch = (
        result.scalars().first()
    )

    if branch is None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No active branch is configured "
                "for the company"
            ),
        )

    return branch


async def _get_supplier_for_update(
    session: AsyncSession,
    *,
    company_id: int,
    supplier_id: int,
) -> Supplier:
    result = await session.execute(
        select(Supplier)
        .where(
            Supplier.id
            == supplier_id,
            Supplier.company_id
            == company_id,
        )
        .with_for_update()
    )

    supplier = (
        result.scalar_one_or_none()
    )

    if supplier is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Supplier was not found",
        )

    if not supplier.is_active:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail="Supplier is inactive",
        )

    return supplier


async def _get_supplier_invoice_or_404(
    session: AsyncSession,
    *,
    company_id: int,
    supplier_invoice_id: int,
    for_update: bool = False,
) -> SupplierInvoice:
    statement = (
        select(SupplierInvoice)
        .options(
            selectinload(
                SupplierInvoice.payments
            )
        )
        .where(
            SupplierInvoice.id
            == supplier_invoice_id,
            SupplierInvoice.company_id
            == company_id,
        )
    )

    if for_update:
        statement = (
            statement.with_for_update()
        )

    result = await session.execute(
        statement
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
                "Supplier invoice was not found"
            ),
        )

    return invoice


async def _get_supplier_payment_or_404(
    session: AsyncSession,
    *,
    company_id: int,
    supplier_payment_id: int,
    for_update: bool = False,
) -> SupplierPayment:
    statement = (
        select(SupplierPayment)
        .where(
            SupplierPayment.id
            == supplier_payment_id,
            SupplierPayment.company_id
            == company_id,
        )
    )

    if for_update:
        statement = (
            statement.with_for_update()
        )

    result = await session.execute(
        statement
    )

    payment = (
        result.scalar_one_or_none()
    )

    if payment is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Supplier payment was not found"
            ),
        )

    return payment


def supplier_invoice_aging(
    invoice: SupplierInvoice,
    *,
    today: date | None = None,
) -> tuple[bool, int, str]:
    current_date = (
        today
        if today is not None
        else date.today()
    )

    balance = money(
        invoice.balance_amount
    )

    if (
        invoice.is_reversed
        or balance <= Decimal("0.00")
        or invoice.due_date is None
        or invoice.due_date >= current_date
    ):
        return (
            False,
            0,
            "Current",
        )

    days_overdue = (
        current_date
        - invoice.due_date
    ).days

    if days_overdue <= 30:
        aging_bucket = "1-30 days"
    elif days_overdue <= 60:
        aging_bucket = "31-60 days"
    elif days_overdue <= 90:
        aging_bucket = "61-90 days"
    else:
        aging_bucket = "90+ days"

    return (
        True,
        days_overdue,
        aging_bucket,
    )


async def _build_supplier_invoice_response(
    session: AsyncSession,
    *,
    invoice: SupplierInvoice,
) -> SupplierInvoiceResponse:
    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=invoice.company_id,
            supplier_id=invoice.supplier_id,
        )
    )

    purchase_order_number = None
    grn_number = None

    if invoice.purchase_order_id is not None:
        po = (
            await get_purchase_order_or_404(
                session,
                company_id=invoice.company_id,
                purchase_order_id=(
                    invoice.purchase_order_id
                ),
            )
        )

        purchase_order_number = (
            po.purchase_order_number
        )

    if invoice.goods_receipt_id is not None:
        receipt = (
            await _get_goods_receipt_or_404(
                session,
                company_id=invoice.company_id,
                goods_receipt_id=(
                    invoice.goods_receipt_id
                ),
            )
        )

        grn_number = (
            receipt.grn_number
        )

    if invoice.invoice_number is None:
        raise RuntimeError(
            "Supplier invoice number missing"
        )

    (
        is_overdue,
        days_overdue,
        aging_bucket,
    ) = supplier_invoice_aging(
        invoice
    )

    return SupplierInvoiceResponse(
        id=invoice.id,
        invoice_number=(
            invoice.invoice_number
        ),
        supplier_id=invoice.supplier_id,
        supplier_name=(
            supplier.company_name
        ),
        purchase_order_id=(
            invoice.purchase_order_id
        ),
        purchase_order_number=(
            purchase_order_number
        ),
        goods_receipt_id=(
            invoice.goods_receipt_id
        ),
        grn_number=grn_number,
        supplier_invoice_number=(
            invoice.supplier_invoice_number
        ),
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        subtotal=money(invoice.subtotal),
        discount_amount=money(
            invoice.discount_amount
        ),
        tax_amount=money(
            invoice.tax_amount
        ),
        grand_total=money(
            invoice.grand_total
        ),
        paid_amount=money(
            invoice.paid_amount
        ),
        balance_amount=money(
            invoice.balance_amount
        ),
        is_overdue=is_overdue,
        days_overdue=days_overdue,
        aging_bucket=aging_bucket,
        status=invoice.status,
        notes=invoice.notes,
        is_reversed=(
            invoice.is_reversed
        ),
        created_at=invoice.created_at,
    )


async def _build_supplier_payment_response(
    session: AsyncSession,
    *,
    payment: SupplierPayment,
) -> SupplierPaymentResponse:
    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=payment.company_id,
            supplier_id=payment.supplier_id,
        )
    )

    supplier_invoice_number = None

    if (
        payment.supplier_invoice_id
        is not None
    ):
        invoice = (
            await _get_supplier_invoice_or_404(
                session,
                company_id=payment.company_id,
                supplier_invoice_id=(
                    payment
                    .supplier_invoice_id
                ),
            )
        )

        supplier_invoice_number = (
            invoice.invoice_number
        )

    if payment.payment_number is None:
        raise RuntimeError(
            "Supplier payment number missing"
        )

    return SupplierPaymentResponse(
        id=payment.id,
        payment_number=(
            payment.payment_number
        ),
        supplier_id=payment.supplier_id,
        supplier_name=(
            supplier.company_name
        ),
        supplier_invoice_id=(
            payment.supplier_invoice_id
        ),
        supplier_invoice_number=(
            supplier_invoice_number
        ),
        amount=money(payment.amount),
        payment_method=(
            payment.payment_method
        ),
        reference_number=(
            payment.reference_number
        ),
        payment_date=(
            payment.payment_date
        ),
        status=payment.status,
        is_reversed=(
            payment.is_reversed
        ),
        notes=payment.notes,
        created_at=payment.created_at,
    )


async def create_supplier_invoice(
    session: AsyncSession,
    *,
    payload: SupplierInvoiceCreate,
    current_user: User,
) -> SupplierInvoiceResponse:
    company = await get_active_company(
        session
    )

    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=company.id,
            supplier_id=payload.supplier_id,
        )
    )

    purchase_order = None
    goods_receipt = None

    if payload.purchase_order_id is not None:
        purchase_order = (
            await get_purchase_order_or_404(
                session,
                company_id=company.id,
                purchase_order_id=(
                    payload.purchase_order_id
                ),
            )
        )

        if (
            purchase_order.supplier_id
            != supplier.id
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Purchase order supplier "
                    "does not match invoice supplier"
                ),
            )

    if payload.goods_receipt_id is not None:
        goods_receipt = (
            await _get_goods_receipt_or_404(
                session,
                company_id=company.id,
                goods_receipt_id=(
                    payload.goods_receipt_id
                ),
            )
        )

        if (
            goods_receipt.supplier_id
            != supplier.id
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Goods receipt supplier "
                    "does not match invoice supplier"
                ),
            )

        if (
            payload.purchase_order_id
            is not None
            and
            goods_receipt.purchase_order_id
            != payload.purchase_order_id
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Goods receipt does not "
                    "belong to purchase order"
                ),
            )

    subtotal = money(
        payload.subtotal
    )

    discount = money(
        payload.discount_amount
    )

    tax = money(
        payload.tax_amount
    )

    if discount > subtotal:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Discount cannot exceed subtotal"
            ),
        )

    grand_total = money(
        subtotal
        - discount
        + tax
    )

    credit_limit = money(
        supplier.credit_limit
    )

    projected_payable = money(
        Decimal(
            supplier.current_payable
        )
        + grand_total
    )

    if (
        credit_limit > Decimal("0.00")
        and projected_payable > credit_limit
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier credit limit would "
                "be exceeded"
            ),
        )

    invoice_date = (
        payload.invoice_date
        or datetime.now(
            timezone.utc
        )
    )

    due_date = payload.due_date

    if due_date is None:
        due_date = (
            invoice_date.date()
            + timedelta(
                days=(
                    supplier
                    .payment_terms_days
                )
            )
        )

    if purchase_order is not None:
        invoice_branch_id = (
            purchase_order.branch_id
        )

    elif goods_receipt is not None:
        invoice_branch_id = (
            goods_receipt.branch_id
        )

    else:
        default_branch = (
            await _get_default_branch_for_company(
                session,
                company_id=company.id,
            )
        )

        invoice_branch_id = (
            default_branch.id
        )

    invoice = SupplierInvoice(
        company_id=company.id,
        branch_id=invoice_branch_id,
        supplier_id=supplier.id,
        purchase_order_id=(
            payload.purchase_order_id
        ),
        goods_receipt_id=(
            payload.goods_receipt_id
        ),
        invoice_number=None,
        supplier_invoice_number=(
            payload
            .supplier_invoice_number
            .strip()
        ),
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        discount_amount=discount,
        tax_amount=tax,
        grand_total=grand_total,
        paid_amount=Decimal(
            "0.00"
        ),
        balance_amount=grand_total,
        status=(
            SupplierInvoiceStatus
            .POSTED
            .value
        ),
        notes=payload.notes,
        posted_by_id=current_user.id,
        posted_at=datetime.now(
            timezone.utc
        ),
        is_reversed=False,
        reversed_by_id=None,
        reversed_at=None,
        reversal_reason=None,
        created_by_id=current_user.id,
    )

    session.add(invoice)

    try:
        await session.flush()

        invoice.invoice_number = (
            f"PINV-{invoice.id:06d}"
        )

        supplier.current_payable = money(
            Decimal(
                supplier.current_payable
            )
            + grand_total
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "supplier_invoice_created"
            ),
            module="purchasing",
            entity_type="supplier_invoice",
            entity_id=invoice.id,
            entity_reference=(
                invoice.invoice_number
            ),
            description=(
                "Supplier invoice created"
            ),
            before_data=None,
            after_data=(
                supplier_invoice_snapshot(
                    invoice
                )
            ),
            metadata={
                "supplier_id":
                    supplier.id,
                "purchase_order_id":
                    payload.purchase_order_id,
                "goods_receipt_id":
                    payload.goods_receipt_id,
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier invoice conflicts "
                "with an existing record"
            ),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    invoice = (
        await _get_supplier_invoice_or_404(
            session,
            company_id=company.id,
            supplier_invoice_id=(
                invoice.id
            ),
        )
    )

    return (
        await _build_supplier_invoice_response(
            session,
            invoice=invoice,
        )
    )


async def list_supplier_invoices(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    supplier_id: int | None,
    status_filter: str | None,
) -> SupplierInvoiceListResponse:
    company = await get_active_company(
        session
    )

    filters = [
        SupplierInvoice.company_id
        == company.id,
    ]

    if supplier_id is not None:
        filters.append(
            SupplierInvoice.supplier_id
            == supplier_id
        )

    if status_filter:
        filters.append(
            SupplierInvoice.status
            == status_filter
        )

    total = int(
        (
            await session.execute(
                select(
                    func.count(
                        SupplierInvoice.id
                    )
                ).where(*filters)
            )
        ).scalar_one()
    )

    result = await session.execute(
        select(SupplierInvoice)
        .where(*filters)
        .order_by(
            SupplierInvoice.id.desc()
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    rows = result.scalars().all()

    return SupplierInvoiceListResponse(
        items=[
            await _build_supplier_invoice_response(
                session,
                invoice=row,
            )
            for row in rows
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


async def get_supplier_invoice(
    session: AsyncSession,
    *,
    supplier_invoice_id: int,
) -> SupplierInvoiceResponse:
    company = await get_active_company(
        session
    )

    invoice = (
        await _get_supplier_invoice_or_404(
            session,
            company_id=company.id,
            supplier_invoice_id=(
                supplier_invoice_id
            ),
        )
    )

    return (
        await _build_supplier_invoice_response(
            session,
            invoice=invoice,
        )
    )


async def reverse_supplier_invoice(
    session: AsyncSession,
    *,
    supplier_invoice_id: int,
    payload: SupplierInvoiceReverseRequest,
    current_user: User,
) -> SupplierInvoiceResponse:
    company = await get_active_company(
        session
    )

    invoice = (
        await _get_supplier_invoice_or_404(
            session,
            company_id=company.id,
            supplier_invoice_id=(
                supplier_invoice_id
            ),
            for_update=True,
        )
    )

    if invoice.is_reversed:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier invoice already reversed"
            ),
        )

    active_payment_total = money(
        sum(
            (
                Decimal(payment.amount)
                for payment
                in invoice.payments
                if not payment.is_reversed
            ),
            Decimal("0.00"),
        )
    )

    if active_payment_total > Decimal(
        "0.00"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Reverse supplier payments "
                "before reversing invoice"
            ),
        )

    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=company.id,
            supplier_id=invoice.supplier_id,
        )
    )

    before = supplier_invoice_snapshot(
        invoice
    )

    balance = money(
        invoice.balance_amount
    )

    if (
        Decimal(
            supplier.current_payable
        )
        < balance
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier payable balance "
                "is inconsistent"
            ),
        )

    try:
        supplier.current_payable = money(
            Decimal(
                supplier.current_payable
            )
            - balance
        )

        invoice.status = (
            SupplierInvoiceStatus
            .REVERSED
            .value
        )

        invoice.is_reversed = True
        invoice.reversed_by_id = (
            current_user.id
        )
        invoice.reversed_at = (
            datetime.now(
                timezone.utc
            )
        )
        invoice.reversal_reason = (
            payload.reason.strip()
        )
        invoice.balance_amount = Decimal(
            "0.00"
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "supplier_invoice_reversed"
            ),
            module="purchasing",
            entity_type="supplier_invoice",
            entity_id=invoice.id,
            entity_reference=(
                invoice.invoice_number
            ),
            description=(
                "Supplier invoice reversed"
            ),
            before_data=before,
            after_data=(
                supplier_invoice_snapshot(
                    invoice
                )
            ),
            metadata={
                "reason":
                    payload.reason.strip()
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except Exception:
        await session.rollback()
        raise

    invoice = (
        await _get_supplier_invoice_or_404(
            session,
            company_id=company.id,
            supplier_invoice_id=(
                invoice.id
            ),
        )
    )

    return (
        await _build_supplier_invoice_response(
            session,
            invoice=invoice,
        )
    )


async def create_supplier_payment(
    session: AsyncSession,
    *,
    payload: SupplierPaymentCreate,
    current_user: User,
) -> SupplierPaymentResponse:
    company = await get_active_company(
        session
    )

    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=company.id,
            supplier_id=payload.supplier_id,
        )
    )

    method = (
        payload.payment_method
        .strip()
        .lower()
    )

    if (
        method
        not in ALLOWED_SUPPLIER_PAYMENT_METHODS
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Unsupported supplier payment method"
            ),
        )

    amount = money(
        payload.amount
    )

    invoice = None

    if (
        payload.supplier_invoice_id
        is not None
    ):
        invoice = (
            await _get_supplier_invoice_or_404(
                session,
                company_id=company.id,
                supplier_invoice_id=(
                    payload
                    .supplier_invoice_id
                ),
                for_update=True,
            )
        )

        if (
            invoice.supplier_id
            != supplier.id
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Invoice supplier does "
                    "not match payment supplier"
                ),
            )

        if invoice.is_reversed:
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Cannot pay reversed invoice"
                ),
            )

        if amount > money(
            invoice.balance_amount
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Payment exceeds invoice balance"
                ),
            )

    if amount > money(
        supplier.current_payable
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Payment exceeds supplier payable"
            ),
        )

    if invoice is not None:
        payment_branch_id = (
            invoice.branch_id
        )

    else:
        default_branch = (
            await _get_default_branch_for_company(
                session,
                company_id=company.id,
            )
        )

        payment_branch_id = (
            default_branch.id
        )

    payment = SupplierPayment(
        company_id=company.id,
        branch_id=payment_branch_id,
        supplier_id=supplier.id,
        supplier_invoice_id=(
            payload.supplier_invoice_id
        ),
        payment_number=None,
        payment_date=datetime.now(
            timezone.utc
        ),
        amount=amount,
        payment_method=method,
        reference_number=(
            payload.reference_number
        ),
        notes=payload.notes,
        status=(
            SupplierPaymentStatus
            .POSTED
            .value
        ),
        is_reversed=False,
        reversed_by_id=None,
        reversed_at=None,
        reversal_reason=None,
        created_by_id=current_user.id,
    )

    session.add(payment)

    try:
        await session.flush()

        payment.payment_number = (
            f"SPAY-{payment.id:06d}"
        )

        supplier.current_payable = money(
            Decimal(
                supplier.current_payable
            )
            - amount
        )

        if invoice is not None:
            invoice.paid_amount = money(
                Decimal(
                    invoice.paid_amount
                )
                + amount
            )

            invoice.balance_amount = money(
                Decimal(
                    invoice.balance_amount
                )
                - amount
            )

            if invoice.balance_amount <= Decimal(
                "0.00"
            ):
                invoice.balance_amount = Decimal(
                    "0.00"
                )
                invoice.status = (
                    SupplierInvoiceStatus
                    .PAID
                    .value
                )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "supplier_payment_created"
            ),
            module="purchasing",
            entity_type="supplier_payment",
            entity_id=payment.id,
            entity_reference=(
                payment.payment_number
            ),
            description=(
                "Supplier payment posted"
            ),
            before_data=None,
            after_data=(
                supplier_payment_snapshot(
                    payment
                )
            ),
            metadata={
                "supplier_invoice_id":
                    payload
                    .supplier_invoice_id
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier payment conflicts "
                "with an existing record"
            ),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    payment = (
        await _get_supplier_payment_or_404(
            session,
            company_id=company.id,
            supplier_payment_id=(
                payment.id
            ),
        )
    )

    return (
        await _build_supplier_payment_response(
            session,
            payment=payment,
        )
    )


async def reverse_supplier_payment(
    session: AsyncSession,
    *,
    supplier_payment_id: int,
    payload: SupplierPaymentReverseRequest,
    current_user: User,
) -> SupplierPaymentResponse:
    company = await get_active_company(
        session
    )

    payment = (
        await _get_supplier_payment_or_404(
            session,
            company_id=company.id,
            supplier_payment_id=(
                supplier_payment_id
            ),
            for_update=True,
        )
    )

    if payment.is_reversed:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Supplier payment already reversed"
            ),
        )

    supplier = (
        await _get_supplier_for_update(
            session,
            company_id=company.id,
            supplier_id=payment.supplier_id,
        )
    )

    invoice = None

    if (
        payment.supplier_invoice_id
        is not None
    ):
        invoice = (
            await _get_supplier_invoice_or_404(
                session,
                company_id=company.id,
                supplier_invoice_id=(
                    payment
                    .supplier_invoice_id
                ),
                for_update=True,
            )
        )

        if invoice.is_reversed:
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Cannot reverse payment "
                    "after invoice reversal"
                ),
            )

    before = (
        supplier_payment_snapshot(
            payment
        )
    )

    amount = money(
        payment.amount
    )

    try:
        supplier.current_payable = money(
            Decimal(
                supplier.current_payable
            )
            + amount
        )

        if invoice is not None:
            invoice.paid_amount = money(
                Decimal(
                    invoice.paid_amount
                )
                - amount
            )

            invoice.balance_amount = money(
                Decimal(
                    invoice.balance_amount
                )
                + amount
            )

            invoice.status = (
                SupplierInvoiceStatus
                .POSTED
                .value
            )

        payment.status = (
            SupplierPaymentStatus
            .REVERSED
            .value
        )
        payment.is_reversed = True
        payment.reversed_by_id = (
            current_user.id
        )
        payment.reversed_at = (
            datetime.now(
                timezone.utc
            )
        )
        payment.reversal_reason = (
            payload.reason.strip()
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "purchasing."
                "supplier_payment_reversed"
            ),
            module="purchasing",
            entity_type="supplier_payment",
            entity_id=payment.id,
            entity_reference=(
                payment.payment_number
            ),
            description=(
                "Supplier payment reversed"
            ),
            before_data=before,
            after_data=(
                supplier_payment_snapshot(
                    payment
                )
            ),
            metadata={
                "reason":
                    payload.reason.strip()
            },
        )

        await session.commit()

    except HTTPException:
        await session.rollback()
        raise

    except Exception:
        await session.rollback()
        raise

    payment = (
        await _get_supplier_payment_or_404(
            session,
            company_id=company.id,
            supplier_payment_id=(
                payment.id
            ),
        )
    )

    return (
        await _build_supplier_payment_response(
            session,
            payment=payment,
        )
    )


async def list_supplier_payments(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    supplier_id: int | None,
) -> SupplierPaymentListResponse:
    company = await get_active_company(
        session
    )

    filters = [
        SupplierPayment.company_id
        == company.id,
    ]

    if supplier_id is not None:
        filters.append(
            SupplierPayment.supplier_id
            == supplier_id
        )

    total = int(
        (
            await session.execute(
                select(
                    func.count(
                        SupplierPayment.id
                    )
                ).where(*filters)
            )
        ).scalar_one()
    )

    result = await session.execute(
        select(SupplierPayment)
        .where(*filters)
        .order_by(
            SupplierPayment.id.desc()
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    rows = result.scalars().all()

    return SupplierPaymentListResponse(
        items=[
            await _build_supplier_payment_response(
                session,
                payment=row,
            )
            for row in rows
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
