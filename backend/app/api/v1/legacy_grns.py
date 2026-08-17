from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.legacy_grn import (
    LegacyGoodsReceiptListResponse,
    LegacyGoodsReceiptResponse,
)
from app.services.legacy_grn import (
    get_legacy_goods_receipt,
    list_legacy_goods_receipts,
)


router = APIRouter(
    prefix="/legacy-grns",
    tags=[
        "Legacy GRN History"
    ],
)


CanViewLegacyGrns = Annotated[
    User,
    Depends(
        require_permission(
            "purchasing.view"
        )
    ),
]


@router.get(
    "",
    response_model=(
        LegacyGoodsReceiptListResponse
    ),
)
async def read_legacy_grns(
    session: DatabaseSession,
    _: CanViewLegacyGrns,
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
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
) -> LegacyGoodsReceiptListResponse:
    return await list_legacy_goods_receipts(
        session,
        page=page,
        page_size=page_size,
        supplier_id=supplier_id,
        search=search,
    )


@router.get(
    "/{legacy_goods_receipt_id}",
    response_model=(
        LegacyGoodsReceiptResponse
    ),
)
async def read_legacy_grn(
    legacy_goods_receipt_id: int,
    session: DatabaseSession,
    _: CanViewLegacyGrns,
) -> LegacyGoodsReceiptResponse:
    return await get_legacy_goods_receipt(
        session,
        legacy_goods_receipt_id=(
            legacy_goods_receipt_id
        ),
    )
