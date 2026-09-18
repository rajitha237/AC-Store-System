from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.cash_book import (
    CashBookListResponse,
    CashBookSummaryResponse,
    ManualCashBookEntryCreate,
    ManualCashBookEntryResponse,
    ManualCashBookEntryReverseRequest,
    ManualCashBookEntryUpdate,
    ManualChequeClearRequest,
)
from app.services.cash_book import (
    cash_book_summary,
    clear_manual_cash_book_cheque,
    create_manual_cash_book_entry,
    delete_manual_cash_book_entry,
    get_active_cash_book_company,
    list_cash_book,
    reverse_manual_cash_book_entry,
    update_manual_cash_book_entry,
)


router = APIRouter(
    prefix="/cash-book",
    tags=["Cash Book"],
)


CanViewCashBook = Annotated[
    User,
    Depends(
        require_permission(
            "payments.view"
        )
    ),
]


CanCreateCashBookEntry = Annotated[
    User,
    Depends(
        require_permission(
            "payments.receive"
        )
    ),
]


CanReverseCashBookEntry = Annotated[
    User,
    Depends(
        require_permission(
            "payments.reverse"
        )
    ),
]


async def _active_company_id(
    session: DatabaseSession,
) -> int:
    try:
        company = (
            await get_active_cash_book_company(
                session
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        ) from exc

    return company.id


@router.post(
    "/manual",
    response_model=ManualCashBookEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_entry(
    payload: ManualCashBookEntryCreate,
    session: DatabaseSession,
    current_user: CanCreateCashBookEntry,
) -> ManualCashBookEntryResponse:
    entry = (
        await create_manual_cash_book_entry(
            session,
            payload=payload,
            current_user=current_user,
        )
    )

    return ManualCashBookEntryResponse.model_validate(
        entry
    )


@router.post(
    "/manual/{entry_id}/reverse",
    response_model=ManualCashBookEntryResponse,
)
async def reverse_manual_entry(
    entry_id: int,
    payload: ManualCashBookEntryReverseRequest,
    session: DatabaseSession,
    current_user: CanReverseCashBookEntry,
) -> ManualCashBookEntryResponse:
    entry = (
        await reverse_manual_cash_book_entry(
            session,
            entry_id=entry_id,
            payload=payload,
            current_user=current_user,
        )
    )

    return ManualCashBookEntryResponse.model_validate(
        entry
    )


@router.patch(
    "/manual/{entry_id}",
    response_model=ManualCashBookEntryResponse,
)
async def update_manual_entry(
    entry_id: int,
    payload: ManualCashBookEntryUpdate,
    session: DatabaseSession,
    current_user: CanReverseCashBookEntry,
) -> ManualCashBookEntryResponse:
    entry = await update_manual_cash_book_entry(
        session,
        entry_id=entry_id,
        payload=payload,
        current_user=current_user,
    )

    return ManualCashBookEntryResponse.model_validate(
        entry
    )


@router.post(
    "/manual/{entry_id}/confirm-cheque",
    response_model=ManualCashBookEntryResponse,
)
async def confirm_manual_cheque(
    entry_id: int,
    payload: ManualChequeClearRequest,
    session: DatabaseSession,
    current_user: CanReverseCashBookEntry,
) -> ManualCashBookEntryResponse:
    entry = await clear_manual_cash_book_cheque(
        session,
        entry_id=entry_id,
        payload=payload,
        current_user=current_user,
    )

    return ManualCashBookEntryResponse.model_validate(
        entry
    )


@router.delete(
    "/manual/{entry_id}",
    response_model=ManualCashBookEntryResponse,
)
async def delete_manual_entry(
    entry_id: int,
    session: DatabaseSession,
    current_user: CanReverseCashBookEntry,
) -> ManualCashBookEntryResponse:
    entry = await delete_manual_cash_book_entry(
        session,
        entry_id=entry_id,
        current_user=current_user,
    )

    return ManualCashBookEntryResponse.model_validate(
        entry
    )


@router.get(
    "",
    response_model=CashBookListResponse,
)
async def read_cash_book(
    session: DatabaseSession,
    _: CanViewCashBook,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),
    date_from: date | None = Query(
        default=None,
    ),
    date_to: date | None = Query(
        default=None,
    ),
) -> CashBookListResponse:
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "date_from cannot be after date_to"
            ),
        )

    company_id = await _active_company_id(
        session
    )

    return await list_cash_book(
        session,
        company_id=company_id,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=CashBookSummaryResponse,
)
async def read_cash_book_summary(
    session: DatabaseSession,
    _: CanViewCashBook,
    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),
    date_from: date | None = Query(
        default=None,
    ),
    date_to: date | None = Query(
        default=None,
    ),
) -> CashBookSummaryResponse:
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "date_from cannot be after date_to"
            ),
        )

    company_id = await _active_company_id(
        session
    )

    return await cash_book_summary(
        session,
        company_id=company_id,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )
