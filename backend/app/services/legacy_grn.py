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
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from sqlalchemy.orm import (
    selectinload,
)

from app.models import (
    Company,
    LegacyGoodsReceipt,
    Supplier,
)
from app.schemas.legacy_grn import (
    LegacyGoodsReceiptItemResponse,
    LegacyGoodsReceiptListItem,
    LegacyGoodsReceiptListResponse,
    LegacyGoodsReceiptResponse,
)


async def _get_active_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(
            Company.is_active.is_(True)
        )
        .order_by(
            Company.id
        )
    )

    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Active company record "
                "is not configured"
            ),
        )

    return company


async def _supplier_name_map(
    session: AsyncSession,
    supplier_ids: set[int],
) -> dict[int, str]:
    if not supplier_ids:
        return {}

    result = await session.execute(
        select(
            Supplier.id,
            Supplier.company_name,
        )
        .where(
            Supplier.id.in_(
                supplier_ids
            )
        )
    )

    return {
        supplier_id: company_name
        for (
            supplier_id,
            company_name,
        ) in result.all()
    }


def _build_list_item(
    receipt: LegacyGoodsReceipt,
    *,
    supplier_name: str | None,
    item_count: int,
) -> LegacyGoodsReceiptListItem:
    return LegacyGoodsReceiptListItem(
        id=receipt.id,
        supplier_id=receipt.supplier_id,
        supplier_name=supplier_name,
        legacy_internal_id=(
            receipt.legacy_internal_id
        ),
        legacy_supplier_id=(
            receipt.legacy_supplier_id
        ),
        legacy_grn_id=(
            receipt.legacy_grn_id
        ),
        legacy_grn_number=(
            receipt.legacy_grn_number
        ),
        reference_invoice_number=(
            receipt
            .reference_invoice_number
        ),
        receipt_date=(
            receipt.receipt_date
        ),
        total_amount=(
            receipt.total_amount
        ),
        discount_amount=(
            receipt.discount_amount
        ),
        net_total=(
            receipt.net_total
        ),
        paid_amount=(
            receipt.paid_amount
        ),
        outstanding_amount=(
            receipt.outstanding_amount
        ),
        legacy_status=(
            receipt.legacy_status
        ),
        source_system=(
            receipt.source_system
        ),
        item_count=item_count,
        created_at=(
            receipt.created_at
        ),
    )


async def list_legacy_goods_receipts(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    supplier_id: int | None,
    search: str | None,
) -> LegacyGoodsReceiptListResponse:
    company = await _get_active_company(
        session
    )

    filters = [
        LegacyGoodsReceipt.company_id
        == company.id,
    ]

    if supplier_id is not None:
        filters.append(
            LegacyGoodsReceipt.supplier_id
            == supplier_id
        )

    normalized_search = (
        search.strip()
        if search
        else None
    )

    if normalized_search:
        pattern = (
            f"%{normalized_search}%"
        )

        filters.append(
            or_(
                LegacyGoodsReceipt
                .legacy_grn_number
                .ilike(pattern),

                LegacyGoodsReceipt
                .legacy_grn_id
                .ilike(pattern),

                LegacyGoodsReceipt
                .reference_invoice_number
                .ilike(pattern),
            )
        )

    total = int(
        (
            await session.execute(
                select(
                    func.count(
                        LegacyGoodsReceipt.id
                    )
                )
                .where(
                    *filters
                )
            )
        ).scalar_one()
    )

    statement = (
        select(
            LegacyGoodsReceipt,
            func.count(
                LegacyGoodsReceipt
                .items
                .property
                .mapper
                .class_
                .id
            ).label(
                "item_count"
            ),
        )
    )

    # Build the item count through the actual
    # legacy item table instead of loading
    # every item for the list endpoint.
    from app.models import (
        LegacyGoodsReceiptItem,
    )

    statement = (
        select(
            LegacyGoodsReceipt,
            func.count(
                LegacyGoodsReceiptItem.id
            ).label(
                "item_count"
            ),
        )
        .outerjoin(
            LegacyGoodsReceiptItem,
            LegacyGoodsReceiptItem
            .legacy_goods_receipt_id
            == LegacyGoodsReceipt.id,
        )
        .where(
            *filters
        )
        .group_by(
            LegacyGoodsReceipt.id
        )
        .order_by(
            LegacyGoodsReceipt
            .receipt_date
            .desc(),
            LegacyGoodsReceipt
            .id
            .desc(),
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(
            page_size
        )
    )

    result = await session.execute(
        statement
    )

    rows = result.all()

    supplier_ids = {
        receipt.supplier_id
        for receipt, _ in rows
    }

    names = await _supplier_name_map(
        session,
        supplier_ids,
    )

    items = [
        _build_list_item(
            receipt,
            supplier_name=names.get(
                receipt.supplier_id
            ),
            item_count=int(
                item_count or 0
            ),
        )
        for (
            receipt,
            item_count,
        ) in rows
    ]

    return (
        LegacyGoodsReceiptListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(
                ceil(
                    total / page_size
                )
                if total
                else 0
            ),
        )
    )


async def get_legacy_goods_receipt(
    session: AsyncSession,
    *,
    legacy_goods_receipt_id: int,
) -> LegacyGoodsReceiptResponse:
    company = await _get_active_company(
        session
    )

    result = await session.execute(
        select(
            LegacyGoodsReceipt
        )
        .options(
            selectinload(
                LegacyGoodsReceipt.items
            )
        )
        .where(
            LegacyGoodsReceipt.id
            == legacy_goods_receipt_id,
            LegacyGoodsReceipt.company_id
            == company.id,
        )
    )

    receipt = (
        result.scalars().first()
    )

    if receipt is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Legacy goods receipt "
                "was not found"
            ),
        )

    names = await _supplier_name_map(
        session,
        {
            receipt.supplier_id
        },
    )

    base = _build_list_item(
        receipt,
        supplier_name=names.get(
            receipt.supplier_id
        ),
        item_count=len(
            receipt.items
        ),
    )

    return LegacyGoodsReceiptResponse(
        **base.model_dump(),
        items=[
            LegacyGoodsReceiptItemResponse
            .model_validate(item)
            for item in receipt.items
        ],
        source_payload=(
            receipt.source_payload
        ),
    )
