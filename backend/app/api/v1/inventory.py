from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import (
    SerialNumberStatus,
    User,
    Warehouse,
    StockMovementType,
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
    WarehouseResponse,
)
from app.services.inventory import (
    build_serial_detail,
    get_serial_or_404,
    issue_non_serialized_stock,
    issue_serialized_stock,
    list_serial_numbers,
    list_stock_balances,
    list_stock_movements,
    receive_non_serialized_stock,
    receive_serialized_stock,
)


from app.schemas.inventory import StockAdjustmentRequest, StockAdjustmentResponse
from app.services.inventory import adjust_non_serialized_stock

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)

CanViewInventory = Annotated[
    User,
    Depends(require_permission("inventory.view")),
]

CanReceiveInventory = Annotated[
    User,
    Depends(require_permission("inventory.receive")),
]

CanAdjustInventory = Annotated[
    User,
    Depends(require_permission("inventory.adjust")),
]


@router.get(
    "/warehouses",
    response_model=list[WarehouseResponse],
)
async def read_warehouses(
    session: DatabaseSession,
    _: CanViewInventory,
    is_active: bool | None = True,
) -> list[WarehouseResponse]:
    statement = select(Warehouse)

    if is_active is not None:
        statement = statement.where(
            Warehouse.is_active.is_(is_active)
        )

    statement = statement.order_by(
        Warehouse.name,
        Warehouse.id,
    )

    result = await session.execute(statement)

    return [
        WarehouseResponse.model_validate(warehouse)
        for warehouse in result.scalars().all()
    ]


@router.post(
    "/receive/serialized",
    response_model=SerializedStockReceiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def receive_serialized_inventory(
    payload: SerializedStockReceiveRequest,
    session: DatabaseSession,
    current_user: CanReceiveInventory,
) -> SerializedStockReceiveResponse:
    return await receive_serialized_stock(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/receive/non-serialized",
    response_model=NonSerializedStockReceiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def receive_non_serialized_inventory(
    payload: NonSerializedStockReceiveRequest,
    session: DatabaseSession,
    current_user: CanReceiveInventory,
) -> NonSerializedStockReceiveResponse:
    return await receive_non_serialized_stock(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/serial-numbers",
    response_model=list[SerialNumberDetailResponse],
)
async def read_serial_numbers(
    session: DatabaseSession,
    _: CanViewInventory,
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    product_id: int | None = Query(
        default=None,
        ge=1,
    ),
    warehouse_id: int | None = Query(
        default=None,
        ge=1,
    ),
    serial_status: SerialNumberStatus | None = None,
) -> list[SerialNumberDetailResponse]:
    return await list_serial_numbers(
        session=session,
        search=search,
        product_id=product_id,
        warehouse_id=warehouse_id,
        serial_status=(
            serial_status.value
            if serial_status is not None
            else None
        ),
    )


@router.get(
    "/serial-numbers/{serial_number_id}",
    response_model=SerialNumberDetailResponse,
)
async def read_serial_number(
    serial_number_id: int,
    session: DatabaseSession,
    _: CanViewInventory,
) -> SerialNumberDetailResponse:
    serial_record = await get_serial_or_404(
        session,
        serial_number_id,
    )

    return await build_serial_detail(
        session,
        serial_record,
    )


@router.post(
    "/issue/serialized",
    response_model=SerializedStockIssueResponse,
)
async def issue_serialized_inventory(
    payload: SerializedStockIssueRequest,
    session: DatabaseSession,
    current_user: CanAdjustInventory,
) -> SerializedStockIssueResponse:
    return await issue_serialized_stock(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/issue/non-serialized",
    response_model=NonSerializedStockIssueResponse,
)
async def issue_non_serialized_inventory(
    payload: NonSerializedStockIssueRequest,
    session: DatabaseSession,
    current_user: CanAdjustInventory,
) -> NonSerializedStockIssueResponse:
    return await issue_non_serialized_stock(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/balances",
    response_model=list[StockBalanceResponse],
)
async def read_stock_balances(
    session: DatabaseSession,
    _: CanViewInventory,
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    warehouse_id: int | None = Query(
        default=None,
        ge=1,
    ),
    product_id: int | None = Query(
        default=None,
        ge=1,
    ),
    low_stock_only: bool = False,
) -> list[StockBalanceResponse]:
    return await list_stock_balances(
        session=session,
        search=search,
        warehouse_id=warehouse_id,
        product_id=product_id,
        low_stock_only=low_stock_only,
    )


@router.get(
    "/movements",
    response_model=StockMovementListResponse,
)
async def read_stock_movements(
    session: DatabaseSession,
    _: CanViewInventory,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    product_id: int | None = Query(
        default=None,
        ge=1,
    ),
    warehouse_id: int | None = Query(
        default=None,
        ge=1,
    ),
    serial_number_id: int | None = Query(
        default=None,
        ge=1,
    ),
    movement_type: StockMovementType | None = Query(
        default=None,
    ),
) -> StockMovementListResponse:
    return await list_stock_movements(
        session=session,
        page=page,
        page_size=page_size,
        product_id=product_id,
        warehouse_id=warehouse_id,
        serial_number_id=serial_number_id,
        movement_type=(
            movement_type.value
            if movement_type is not None
            else None
        ),
    )



@router.post(
    "/adjust",
    response_model=StockAdjustmentResponse,
)
async def adjust_inventory_stock(
    payload: StockAdjustmentRequest,
    session: DatabaseSession,
    current_user: CanAdjustInventory,
) -> StockAdjustmentResponse:
    result = await adjust_non_serialized_stock(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return StockAdjustmentResponse(
        **result
    )



from app.schemas.inventory import (
    NonSerializedStockTransferRequest,
    NonSerializedStockTransferResponse,
    SerializedStockTransferRequest,
    SerializedStockTransferResponse,
)
from app.services.inventory import (
    transfer_non_serialized_stock,
    transfer_serialized_stock,
)



@router.post(
    "/transfer/non-serialized",
    response_model=
        NonSerializedStockTransferResponse,
)
async def transfer_non_serialized_inventory(
    payload:
        NonSerializedStockTransferRequest,
    session: DatabaseSession,
    current_user: CanAdjustInventory,
) -> NonSerializedStockTransferResponse:
    result = (
        await transfer_non_serialized_stock(
            session=session,
            payload=payload,
            current_user=current_user,
        )
    )

    return (
        NonSerializedStockTransferResponse(
            **result
        )
    )


@router.post(
    "/transfer/serialized",
    response_model=
        SerializedStockTransferResponse,
)
async def transfer_serialized_inventory(
    payload:
        SerializedStockTransferRequest,
    session: DatabaseSession,
    current_user: CanAdjustInventory,
) -> SerializedStockTransferResponse:
    result = (
        await transfer_serialized_stock(
            session=session,
            payload=payload,
            current_user=current_user,
        )
    )

    return (
        SerializedStockTransferResponse(
            **result
        )
    )
