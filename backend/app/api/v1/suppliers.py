from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier import (
    create_supplier,
    get_supplier_or_404,
    list_suppliers,
    update_supplier,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
)

CanViewSuppliers = Annotated[
    User,
    Depends(require_permission("suppliers.view")),
]

CanManageSuppliers = Annotated[
    User,
    Depends(require_permission("suppliers.manage")),
]


@router.get(
    "",
    response_model=SupplierListResponse,
)
async def read_suppliers(
    session: DatabaseSession,
    _: CanViewSuppliers,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    is_active: bool | None = None,
) -> SupplierListResponse:
    return await list_suppliers(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_record(
    payload: SupplierCreate,
    session: DatabaseSession,
    current_user: CanManageSuppliers,
) -> SupplierResponse:
    supplier = await create_supplier(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return SupplierResponse.model_validate(supplier)


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
async def read_supplier(
    supplier_id: int,
    session: DatabaseSession,
    _: CanViewSuppliers,
) -> SupplierResponse:
    supplier = await get_supplier_or_404(
        session=session,
        supplier_id=supplier_id,
    )

    return SupplierResponse.model_validate(supplier)


@router.patch(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
async def update_supplier_record(
    supplier_id: int,
    payload: SupplierUpdate,
    session: DatabaseSession,
    current_user: CanManageSuppliers,
) -> SupplierResponse:
    supplier = await get_supplier_or_404(
        session=session,
        supplier_id=supplier_id,
    )

    updated_supplier = await update_supplier(
        session=session,
        supplier=supplier,
        payload=payload,
        current_user=current_user,
    )

    return SupplierResponse.model_validate(
        updated_supplier
    )


@router.delete(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
async def deactivate_supplier(
    supplier_id: int,
    session: DatabaseSession,
    current_user: CanManageSuppliers,
) -> SupplierResponse:
    supplier = await get_supplier_or_404(
        session=session,
        supplier_id=supplier_id,
    )

    updated_supplier = await update_supplier(
        session=session,
        supplier=supplier,
        payload=SupplierUpdate(is_active=False),
        current_user=current_user,
    )

    return SupplierResponse.model_validate(
        updated_supplier
    )
