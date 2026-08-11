from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import (
    PurchaseOrderStatus,
    User,
)
from app.schemas.purchasing import (
    GoodsReceiptCreate,
    GoodsReceiptListResponse,
    GoodsReceiptResponse,
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
    PurchaseOrderListResponse,
    PurchaseOrderUpdate,
)
from app.services.purchasing import (
    approve_purchase_order,
    cancel_purchase_order,
    create_purchase_order,
    get_goods_receipt,
    get_purchase_order,
    list_goods_receipts,
    list_purchase_orders,
    receive_purchase_order,
    create_supplier_invoice,
    create_supplier_payment,
    get_supplier_invoice,
    list_supplier_invoices,
    list_supplier_payments,
    reverse_supplier_invoice,
    reverse_supplier_payment,
    update_purchase_order,
)


router = APIRouter(
    prefix="/purchase-orders",
    tags=["Purchasing"],
)


CanViewPurchasing = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.view"
        )
    ),
]


CanManagePurchasing = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.manage"
        )
    ),
]


CanApprovePurchasing = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.approve"
        )
    ),
]


CanReceivePurchasing = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.receive"
        )
    ),
]


CanManageSupplierFinance = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.finance"
        )
    ),
]


@router.get(
    "",
    response_model=(
        PurchaseOrderListResponse
    ),
)
async def read_purchase_orders(
    session: DatabaseSession,
    _: CanViewPurchasing,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    order_status:
        PurchaseOrderStatus
        | None = Query(
            default=None,
        ),
    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),
    warehouse_id: int | None = Query(
        default=None,
        ge=1,
    ),
) -> PurchaseOrderListResponse:
    return await list_purchase_orders(
        session,
        page=page,
        page_size=page_size,
        search=search,
        order_status=order_status,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
    )


@router.post(
    "",
    response_model=(
        PurchaseOrderDetailResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_purchase_order_record(
    payload: PurchaseOrderCreate,
    session: DatabaseSession,
    current_user: CanManagePurchasing,
) -> PurchaseOrderDetailResponse:
    return await create_purchase_order(
        session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/goods-receipts",
    response_model=GoodsReceiptListResponse,
)
async def read_goods_receipts(
    session: DatabaseSession,
    _: CanViewPurchasing,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    purchase_order_id: int | None = Query(
        default=None,
        ge=1,
    ),
    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),
) -> GoodsReceiptListResponse:
    return await list_goods_receipts(
        session,
        page=page,
        page_size=page_size,
        purchase_order_id=purchase_order_id,
        supplier_id=supplier_id,
    )

@router.get(
    "/goods-receipts/{goods_receipt_id}",
    response_model=GoodsReceiptResponse,
)
async def read_goods_receipt(
    goods_receipt_id: int,
    session: DatabaseSession,
    _: CanViewPurchasing,
) -> GoodsReceiptResponse:
    return await get_goods_receipt(
        session,
        goods_receipt_id=goods_receipt_id,
    )

@router.get(
    "/{purchase_order_id}",
    response_model=(
        PurchaseOrderDetailResponse
    ),
)
async def read_purchase_order(
    purchase_order_id: int,
    session: DatabaseSession,
    _: CanViewPurchasing,
) -> PurchaseOrderDetailResponse:
    return await get_purchase_order(
        session,
        purchase_order_id=(
            purchase_order_id
        ),
    )


@router.patch(
    "/{purchase_order_id}",
    response_model=(
        PurchaseOrderDetailResponse
    ),
)
async def update_purchase_order_record(
    purchase_order_id: int,
    payload: PurchaseOrderUpdate,
    session: DatabaseSession,
    current_user: CanManagePurchasing,
) -> PurchaseOrderDetailResponse:
    return await update_purchase_order(
        session,
        purchase_order_id=(
            purchase_order_id
        ),
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{purchase_order_id}/approve",
    response_model=(
        PurchaseOrderDetailResponse
    ),
)
async def approve_purchase_order_record(
    purchase_order_id: int,
    session: DatabaseSession,
    current_user: CanApprovePurchasing,
) -> PurchaseOrderDetailResponse:
    return await approve_purchase_order(
        session,
        purchase_order_id=(
            purchase_order_id
        ),
        current_user=current_user,
    )


@router.post(
    "/{purchase_order_id}/cancel",
    response_model=(
        PurchaseOrderDetailResponse
    ),
)
async def cancel_purchase_order_record(
    purchase_order_id: int,
    payload: PurchaseOrderCancelRequest,
    session: DatabaseSession,
    current_user: CanManagePurchasing,
) -> PurchaseOrderDetailResponse:
    return await cancel_purchase_order(
        session,
        purchase_order_id=(
            purchase_order_id
        ),
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{purchase_order_id}/receive",
    response_model=GoodsReceiptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def receive_purchase_order_record(
    purchase_order_id: int,
    payload: GoodsReceiptCreate,
    session: DatabaseSession,
    current_user: CanReceivePurchasing,
) -> GoodsReceiptResponse:
    return await receive_purchase_order(
        session,
        purchase_order_id=purchase_order_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/supplier-invoices",
    response_model=SupplierInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_invoice_record(
    payload: SupplierInvoiceCreate,
    session: DatabaseSession,
    current_user: CanManageSupplierFinance,
) -> SupplierInvoiceResponse:
    return await create_supplier_invoice(
        session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/supplier-invoices",
    response_model=SupplierInvoiceListResponse,
)
async def read_supplier_invoices(
    session: DatabaseSession,
    _: CanViewPurchasing,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
) -> SupplierInvoiceListResponse:
    return await list_supplier_invoices(
        session,
        page=page,
        page_size=page_size,
        supplier_id=supplier_id,
        status_filter=status_filter,
    )


@router.get(
    "/supplier-invoices/{supplier_invoice_id}",
    response_model=SupplierInvoiceResponse,
)
async def read_supplier_invoice(
    supplier_invoice_id: int,
    session: DatabaseSession,
    _: CanViewPurchasing,
) -> SupplierInvoiceResponse:
    return await get_supplier_invoice(
        session,
        supplier_invoice_id=(
            supplier_invoice_id
        ),
    )


@router.post(
    "/supplier-invoices/{supplier_invoice_id}/reverse",
    response_model=SupplierInvoiceResponse,
)
async def reverse_supplier_invoice_record(
    supplier_invoice_id: int,
    payload: SupplierInvoiceReverseRequest,
    session: DatabaseSession,
    current_user: CanManageSupplierFinance,
) -> SupplierInvoiceResponse:
    return await reverse_supplier_invoice(
        session,
        supplier_invoice_id=(
            supplier_invoice_id
        ),
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/supplier-payments",
    response_model=SupplierPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_payment_record(
    payload: SupplierPaymentCreate,
    session: DatabaseSession,
    current_user: CanManageSupplierFinance,
) -> SupplierPaymentResponse:
    return await create_supplier_payment(
        session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/supplier-payments",
    response_model=SupplierPaymentListResponse,
)
async def read_supplier_payments(
    session: DatabaseSession,
    _: CanViewPurchasing,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),
) -> SupplierPaymentListResponse:
    return await list_supplier_payments(
        session,
        page=page,
        page_size=page_size,
        supplier_id=supplier_id,
    )


@router.post(
    "/supplier-payments/{supplier_payment_id}/reverse",
    response_model=SupplierPaymentResponse,
)
async def reverse_supplier_payment_record(
    supplier_payment_id: int,
    payload: SupplierPaymentReverseRequest,
    session: DatabaseSession,
    current_user: CanManageSupplierFinance,
) -> SupplierPaymentResponse:
    return await reverse_supplier_payment(
        session,
        supplier_payment_id=(
            supplier_payment_id
        ),
        payload=payload,
        current_user=current_user,
    )

