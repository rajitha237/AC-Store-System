from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_book import ManualCashBookEntry
from app.models.company import Branch, Company
from app.models.purchasing import SupplierPayment
from app.models.sales import (
    CustomerPayment,
    PaymentMethod,
)
from app.models.user import User
from app.schemas.cash_book import (
    CashBookListResponse,
    CashBookSummaryResponse,
    CashBookTransactionResponse,
    ManualCashBookEntryCreate,
    ManualCashBookEntryReverseRequest,
    ManualCashBookEntryUpdate,
    ManualChequeClearRequest,
)
from app.services.audit import create_audit_log


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(
    value: Decimal | int | float | str,
) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )





def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


async def get_active_cash_book_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(
            Company.is_active.is_(True)
        )
        .order_by(
            Company.id.asc()
        )
        .limit(1)
    )

    company = result.scalar_one_or_none()

    if company is None:
        raise ValueError(
            "No active company is configured"
        )

    return company



async def get_cash_book_branch(
    session: AsyncSession,
    *,
    company_id: int,
) -> Branch:
    result = await session.execute(
        select(Branch)
        .where(
            Branch.company_id
            == company_id,
            Branch.is_active.is_(
                True
            ),
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
        from fastapi import (
            HTTPException,
            status,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No active branch is "
                "configured for the company"
            ),
        )

    return branch


def manual_cash_book_snapshot(
    entry: ManualCashBookEntry,
) -> dict:
    return {
        "id": entry.id,
        "entry_number":
            entry.entry_number,
        "company_id":
            entry.company_id,
        "branch_id":
            entry.branch_id,
        "entry_type":
            entry.entry_type,
        "entry_date":
            entry.entry_date,
        "amount":
            str(
                money(
                    entry.amount
                )
            ),
        "payment_method":
            entry.payment_method,
        "cheque_date":
            (
                entry.cheque_date.isoformat()
                if entry.cheque_date
                else None
            ),
        "cheque_status":
            entry.cheque_status,
        "cheque_cleared_at":
            (
                entry.cheque_cleared_at.isoformat()
                if entry.cheque_cleared_at
                else None
            ),
        "cheque_cleared_by_id":
            entry.cheque_cleared_by_id,
        "category":
            entry.category,
        "description":
            entry.description,
        "reference_number":
            entry.reference_number,
        "notes":
            entry.notes,
        "created_by_id":
            entry.created_by_id,
        "reversed_at":
            entry.reversed_at,
        "reversed_by_id":
            entry.reversed_by_id,
        "reversal_reason":
            entry.reversal_reason,
    }


def cash_book_entry_number(
    entry_id: int,
) -> str:
    return (
        f"CB-{entry_id:06d}"
    )


async def create_manual_cash_book_entry(
    session: AsyncSession,
    *,
    payload: ManualCashBookEntryCreate,
    current_user: User,
) -> ManualCashBookEntry:
    from uuid import uuid4

    from fastapi import (
        HTTPException,
        status,
    )

    company = (
        await get_active_cash_book_company(
            session
        )
    )

    branch = (
        await get_cash_book_branch(
            session,
            company_id=company.id,
        )
    )

    payment_method = (
        payload.payment_method.value
        if isinstance(
            payload.payment_method,
            PaymentMethod,
        )
        else str(
            payload.payment_method
        )
    )

    temporary_number = (
        "TMP-CB-"
        + uuid4().hex
    )

    is_issued_cheque = (
        payload.entry_type == "cash_out"
        and payload.payment_method
        == PaymentMethod.CHEQUE
    )

    if (
        payload.payment_method
        == PaymentMethod.CHEQUE
        and payload.cheque_date is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail="Cheque date is required",
        )

    business_today = _business_today(
        company.timezone
    )

    if (
        payload.entry_date is not None
        and payload.entry_date > business_today
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Cash Book transaction date "
                "cannot be in the future"
            ),
        )

    entry = ManualCashBookEntry(
        company_id=company.id,
        branch_id=branch.id,
        entry_number=temporary_number,
        entry_type=payload.entry_type,
        entry_date=(
            _business_day_start(
                payload.entry_date,
                company.timezone,
            )
            if payload.entry_date is not None
            else datetime.now(timezone.utc)
        ),
        amount=money(
            payload.amount
        ),
        payment_method=(
            payment_method
        ),
        category=(
            payload.category.strip()
        ),
        description=(
            payload.description.strip()
        ),
        reference_number=(
            payload.reference_number.strip()
            if payload.reference_number
            and payload.reference_number
            .strip()
            else None
        ),
        cheque_date=payload.cheque_date,
        cheque_status=(
            "pending"
            if is_issued_cheque
            else None
        ),
        cheque_cleared_at=None,
        cheque_cleared_by_id=None,
        notes=(
            payload.notes.strip()
            if payload.notes
            and payload.notes.strip()
            else None
        ),
        created_by_id=(
            current_user.id
        ),
    )

    session.add(entry)

    try:
        await session.flush()

        entry.entry_number = (
            cash_book_entry_number(
                entry.id
            )
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "cash_book.manual_entry_created"
            ),
            module="cash_book",
            entity_type=(
                "manual_cash_book_entry"
            ),
            entity_id=entry.id,
            entity_reference=(
                entry.entry_number
            ),
            description=(
                f"Manual cash book entry "
                f"{entry.entry_number} created"
            ),
            before_data=None,
            after_data=(
                manual_cash_book_snapshot(
                    entry
                )
            ),
            metadata={
                "entry_type":
                    entry.entry_type,
                "payment_method":
                    entry.payment_method,
                "branch_id":
                    entry.branch_id,
            },
        )

        await session.commit()
        await session.refresh(entry)

    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Cash book entry could "
                "not be created because "
                "a unique value already "
                "exists"
            ),
        ) from exc

    except Exception:
        await session.rollback()
        raise

    return entry



async def _locked_manual_cash_book_entry(
    session: AsyncSession,
    *,
    entry_id: int,
    company_id: int,
) -> ManualCashBookEntry:
    from fastapi import HTTPException, status

    result = await session.execute(
        select(ManualCashBookEntry)
        .where(
            ManualCashBookEntry.id == entry_id,
            ManualCashBookEntry.company_id
            == company_id,
        )
        .with_for_update()
    )

    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash book entry was not found",
        )

    return entry


async def update_manual_cash_book_entry(
    session: AsyncSession,
    *,
    entry_id: int,
    payload: ManualCashBookEntryUpdate,
    current_user: User,
) -> ManualCashBookEntry:
    from fastapi import HTTPException, status

    entry = await _locked_manual_cash_book_entry(
        session,
        entry_id=entry_id,
        company_id=current_user.company_id,
    )

    company = await get_active_cash_book_company(
        session
    )

    if company.id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash book entry was not found",
        )

    if entry.reversed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A reversed cash book entry "
                "cannot be edited"
            ),
        )

    if (
        entry.entry_type == "cash_out"
        and entry.payment_method == PaymentMethod.CHEQUE.value
        and entry.cheque_status == "cleared"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A cleared issued cheque cannot be edited. "
                "Delete/reverse the entry and create a new one "
                "if a correction is required."
            ),
        )

    is_issued_cheque = (
        payload.entry_type == "cash_out"
        and payload.payment_method
        == PaymentMethod.CHEQUE
    )

    if (
        payload.payment_method
        == PaymentMethod.CHEQUE
        and payload.cheque_date is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail="Cheque date is required",
        )

    if payload.entry_date > _business_today(
        company.timezone
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Cash Book transaction date "
                "cannot be in the future"
            ),
        )

    before_snapshot = manual_cash_book_snapshot(
        entry
    )

    entry.entry_type = payload.entry_type
    entry.entry_date = _business_day_start(
        payload.entry_date,
        company.timezone,
    )
    entry.amount = money(payload.amount)
    entry.payment_method = (
        payload.payment_method.value
    )
    entry.category = payload.category.strip()
    entry.description = (
        payload.description.strip()
    )
    entry.reference_number = (
        payload.reference_number.strip()
        if payload.reference_number
        and payload.reference_number.strip()
        else None
    )
    entry.notes = (
        payload.notes.strip()
        if payload.notes
        and payload.notes.strip()
        else None
    )
    entry.cheque_date = payload.cheque_date

    if is_issued_cheque:
        # Editing an already-cleared cheque keeps its
        # cleared state. Otherwise it is pending.
        if entry.cheque_status != "cleared":
            entry.cheque_status = "pending"
            entry.cheque_cleared_at = None
            entry.cheque_cleared_by_id = None
    else:
        entry.cheque_status = None
        entry.cheque_cleared_at = None
        entry.cheque_cleared_by_id = None

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="cash_book.manual_entry_updated",
            module="cash_book",
            entity_type="manual_cash_book_entry",
            entity_id=entry.id,
            entity_reference=entry.entry_number,
            description=(
                f"Manual cash book entry "
                f"{entry.entry_number} updated"
            ),
            before_data=before_snapshot,
            after_data=manual_cash_book_snapshot(
                entry
            ),
            metadata=None,
        )

        await session.commit()
        await session.refresh(entry)

    except Exception:
        await session.rollback()
        raise

    return entry


async def clear_manual_cash_book_cheque(
    session: AsyncSession,
    *,
    entry_id: int,
    payload: ManualChequeClearRequest,
    current_user: User,
) -> ManualCashBookEntry:
    from fastapi import HTTPException, status

    entry = await _locked_manual_cash_book_entry(
        session,
        entry_id=entry_id,
        company_id=current_user.company_id,
    )

    company = await get_active_cash_book_company(
        session
    )

    if company.id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash book entry was not found",
        )

    if entry.reversed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cash book entry is reversed",
        )

    if not (
        entry.entry_type == "cash_out"
        and entry.payment_method
        == PaymentMethod.CHEQUE.value
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "Only issued cash-out cheques "
                "can be confirmed"
            ),
        )

    if entry.cheque_status == "cleared":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cheque is already confirmed paid",
        )

    if entry.cheque_date is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cheque date is missing",
        )

    if entry.cheque_date > _business_today(
        company.timezone
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cheque cannot be confirmed before "
                "its cheque date"
            ),
        )

    before_snapshot = manual_cash_book_snapshot(
        entry
    )

    entry.cheque_status = "cleared"
    entry.cheque_cleared_at = utc_now()
    entry.cheque_cleared_by_id = current_user.id

    if payload.notes and payload.notes.strip():
        extra = payload.notes.strip()
        entry.notes = (
            f"{entry.notes}\n{extra}"
            if entry.notes
            else extra
        )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="cash_book.cheque_cleared",
            module="cash_book",
            entity_type="manual_cash_book_entry",
            entity_id=entry.id,
            entity_reference=entry.entry_number,
            description=(
                f"Issued cheque for "
                f"{entry.entry_number} confirmed paid"
            ),
            before_data=before_snapshot,
            after_data=manual_cash_book_snapshot(
                entry
            ),
            metadata={
                "cheque_date": (
                    entry.cheque_date.isoformat()
                ),
            },
        )

        await session.commit()
        await session.refresh(entry)

    except Exception:
        await session.rollback()
        raise

    return entry


async def delete_manual_cash_book_entry(
    session: AsyncSession,
    *,
    entry_id: int,
    current_user: User,
) -> ManualCashBookEntry:
    entry = await _locked_manual_cash_book_entry(
        session,
        entry_id=entry_id,
        company_id=current_user.company_id,
    )

    if entry.reversed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cash Book entry is already deleted/reversed",
        )

    before_snapshot = manual_cash_book_snapshot(
        entry
    )

    try:
        entry.reversed_at = datetime.now(
            timezone.utc
        )
        entry.reversed_by_id = current_user.id
        entry.reversal_reason = (
            "Deleted from Cash Book"
        )

        session.add(
            AuditLog(
                company_id=entry.company_id,
                user_id=current_user.id,
                action="cash_book.manual.delete",
                entity_type="manual_cash_book_entry",
                entity_id=entry.id,
                before_data=before_snapshot,
                after_data=manual_cash_book_snapshot(
                    entry
                ),
                metadata={
                    "delete_mode":
                        "audit_preserving_reversal",
                },
            )
        )

        await session.commit()
        await session.refresh(entry)

    except Exception:
        await session.rollback()
        raise

    return entry

async def reverse_manual_cash_book_entry(
    session: AsyncSession,
    *,
    entry_id: int,
    payload: ManualCashBookEntryReverseRequest,
    current_user: User,
) -> ManualCashBookEntry:
    from fastapi import (
        HTTPException,
        status,
    )

    company = (
        await get_active_cash_book_company(
            session
        )
    )

    result = await session.execute(
        select(
            ManualCashBookEntry
        )
        .where(
            ManualCashBookEntry.id
            == entry_id,
            ManualCashBookEntry.company_id
            == company.id,
        )
        .with_for_update()
    )

    entry = (
        result.scalar_one_or_none()
    )

    if entry is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Cash book entry "
                "was not found"
            ),
        )

    if entry.reversed_at is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Cash book entry "
                "is already reversed"
            ),
        )

    before_snapshot = (
        manual_cash_book_snapshot(
            entry
        )
    )

    entry.reversed_at = utc_now()
    entry.reversed_by_id = (
        current_user.id
    )
    entry.reversal_reason = (
        payload.reason.strip()
    )

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=(
                "cash_book.manual_entry_reversed"
            ),
            module="cash_book",
            entity_type=(
                "manual_cash_book_entry"
            ),
            entity_id=entry.id,
            entity_reference=(
                entry.entry_number
            ),
            description=(
                f"Manual cash book entry "
                f"{entry.entry_number} reversed"
            ),
            before_data=(
                before_snapshot
            ),
            after_data=(
                manual_cash_book_snapshot(
                    entry
                )
            ),
            metadata={
                "reversal_reason":
                    entry.reversal_reason,
                "reversal_notes":
                    (
                        payload.notes.strip()
                        if payload.notes
                        and payload.notes.strip()
                        else None
                    ),
            },
        )

        await session.commit()
        await session.refresh(entry)

    except Exception:
        await session.rollback()
        raise

    return entry


def _company_zone(
    timezone_name: str,
) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def _business_today(
    timezone_name: str,
) -> date:
    return (
        datetime.now(timezone.utc)
        .astimezone(
            _company_zone(
                timezone_name
            )
        )
        .date()
    )


def _business_day_start(
    value: date,
    timezone_name: str,
) -> datetime:
    local_start = datetime.combine(
        value,
        time.min,
        tzinfo=_company_zone(
            timezone_name
        ),
    )

    return local_start.astimezone(
        timezone.utc
    )


def _day_start(
    value: date,
) -> datetime:
    return datetime.combine(
        value,
        time.min,
        tzinfo=timezone.utc,
    )


def _next_business_day_start(
    value: date,
    timezone_name: str,
) -> datetime:
    return _business_day_start(
        value + timedelta(days=1),
        timezone_name,
    )


def _next_day_start(
    value: date,
) -> datetime:
    return _day_start(
        value + timedelta(days=1)
    )


def _customer_transaction(
    payment: CustomerPayment,
) -> CashBookTransactionResponse:
    return CashBookTransactionResponse(
        source_type="customer_payment",
        source_id=payment.id,
        source_reference=(
            payment.receipt_number
            or payment.reference_number
        ),
        direction="cash_in",
        transaction_date=payment.payment_date,
        amount=money(payment.amount),
        payment_method=payment.payment_method,
        category="Customer payment",
        description=(
            payment.notes
            or "Customer payment received"
        ),
        branch_id=payment.branch_id,
        status=(
            "reversed"
            if payment.is_reversed
            else "active"
        ),
        cheque_date=payment.cheque_date,
        cheque_status=None,
        cheque_cleared_at=None,
        can_edit=False,
        can_delete=False,
        can_confirm_cheque=False,
        running_balance=None,
    )


def _supplier_transaction(
    payment: SupplierPayment,
) -> CashBookTransactionResponse:
    return CashBookTransactionResponse(
        source_type="supplier_payment",
        source_id=payment.id,
        source_reference=(
            payment.payment_number
            or payment.reference_number
        ),
        direction="cash_out",
        transaction_date=payment.payment_date,
        amount=money(payment.amount),
        payment_method=payment.payment_method,
        category="Supplier payment",
        description=(
            payment.notes
            or "Supplier payment made"
        ),
        branch_id=payment.branch_id,
        status=(
            "reversed"
            if payment.is_reversed
            else payment.status
        ),
        cheque_date=None,
        cheque_status=None,
        cheque_cleared_at=None,
        can_edit=False,
        can_delete=False,
        can_confirm_cheque=False,
        running_balance=None,
    )


def _manual_transaction(
    entry: ManualCashBookEntry,
    *,
    business_today: date | None = None,
) -> CashBookTransactionResponse:
    effective_today = (
        business_today
        if business_today is not None
        else date.today()
    )

    return CashBookTransactionResponse(
        source_type="manual_cash_book",
        source_id=entry.id,
        source_reference=(
            entry.entry_number
            or entry.reference_number
        ),
        direction=entry.entry_type,
        transaction_date=entry.entry_date,
        amount=money(entry.amount),
        payment_method=entry.payment_method,
        category=entry.category,
        description=entry.description,
        reference_number=entry.reference_number,
        notes=entry.notes,
        branch_id=entry.branch_id,
        status=(
            "reversed"
            if entry.reversed_at is not None
            else (
                "pending_cheque"
                if entry.cheque_status
                == "pending"
                else "active"
            )
        ),
        cheque_date=entry.cheque_date,
        cheque_status=entry.cheque_status,
        cheque_cleared_at=(
            entry.cheque_cleared_at
        ),
        can_edit=(
            entry.reversed_at is None
            and not (
                entry.entry_type == "cash_out"
                and entry.payment_method
                == PaymentMethod.CHEQUE.value
                and entry.cheque_status == "cleared"
            )
        ),
        can_delete=(
            entry.reversed_at is None
        ),
        can_confirm_cheque=(
            entry.reversed_at is None
            and entry.entry_type == "cash_out"
            and entry.payment_method
            == PaymentMethod.CHEQUE.value
            and entry.cheque_status == "pending"
            and entry.cheque_date is not None
            and entry.cheque_date <= effective_today
        ),
        running_balance=None,
    )


def _signed_amount(
    transaction: CashBookTransactionResponse,
) -> Decimal:
    if transaction.status == "reversed":
        return ZERO

    if transaction.status == "pending_cheque":
        return ZERO

    if transaction.direction == "cash_in":
        return money(
            transaction.amount
        )

    return money(
        -transaction.amount
    )


async def _load_active_transactions(
    session: AsyncSession,
    *,
    company_id: int,
    branch_id: int | None,
    start_at: datetime | None,
    end_before: datetime | None,
    business_today: date | None = None,
) -> list[CashBookTransactionResponse]:
    customer_stmt = (
        select(CustomerPayment)
        .where(
            CustomerPayment.company_id
            == company_id,
            CustomerPayment.is_reversed
            .is_(False),
        )
    )

    supplier_stmt = (
        select(SupplierPayment)
        .where(
            SupplierPayment.company_id
            == company_id,
            SupplierPayment.is_reversed
            .is_(False),
        )
    )

    manual_stmt = (
        select(ManualCashBookEntry)
        .where(
            ManualCashBookEntry.company_id
            == company_id,
            ManualCashBookEntry.reversed_at
            .is_(None),
        )
    )

    if branch_id is not None:
        customer_stmt = (
            customer_stmt.where(
                CustomerPayment.branch_id
                == branch_id
            )
        )

        supplier_stmt = (
            supplier_stmt.where(
                SupplierPayment.branch_id
                == branch_id
            )
        )

        manual_stmt = (
            manual_stmt.where(
                ManualCashBookEntry.branch_id
                == branch_id
            )
        )

    if start_at is not None:
        customer_stmt = (
            customer_stmt.where(
                CustomerPayment.payment_date
                >= start_at
            )
        )

        supplier_stmt = (
            supplier_stmt.where(
                SupplierPayment.payment_date
                >= start_at
            )
        )

        manual_stmt = (
            manual_stmt.where(
                ManualCashBookEntry.entry_date
                >= start_at
            )
        )

    if end_before is not None:
        customer_stmt = (
            customer_stmt.where(
                CustomerPayment.payment_date
                < end_before
            )
        )

        supplier_stmt = (
            supplier_stmt.where(
                SupplierPayment.payment_date
                < end_before
            )
        )

        manual_stmt = (
            manual_stmt.where(
                ManualCashBookEntry.entry_date
                < end_before
            )
        )

    customer_result = (
        await session.execute(
            customer_stmt
        )
    )

    supplier_result = (
        await session.execute(
            supplier_stmt
        )
    )

    manual_result = (
        await session.execute(
            manual_stmt
        )
    )

    transactions: list[
        CashBookTransactionResponse
    ] = []

    transactions.extend(
        _customer_transaction(
            payment
        )
        for payment
        in customer_result
        .scalars()
        .all()
    )

    transactions.extend(
        _supplier_transaction(
            payment
        )
        for payment
        in supplier_result
        .scalars()
        .all()
    )

    transactions.extend(
        _manual_transaction(
            entry,
            business_today=business_today,
        )
        for entry
        in manual_result
        .scalars()
        .all()
    )

    return transactions


def _net_total(
    transactions: list[
        CashBookTransactionResponse
    ],
) -> Decimal:
    total = ZERO

    for transaction in transactions:
        total = money(
            total
            + _signed_amount(
                transaction
            )
        )

    return money(total)


async def list_cash_book(
    session: AsyncSession,
    *,
    company_id: int,
    branch_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> CashBookListResponse:
    if page < 1:
        raise ValueError(
            "page must be at least 1"
        )

    if page_size < 1:
        raise ValueError(
            "page_size must be at least 1"
        )

    company_result = await session.execute(
        select(Company).where(
            Company.id == company_id,
            Company.is_active.is_(True),
        )
    )

    company = (
        company_result.scalar_one_or_none()
    )

    if company is None:
        raise ValueError(
            "Active company was not found"
        )

    business_today = _business_today(
        company.timezone
    )

    start_at = (
        _business_day_start(
            date_from,
            company.timezone,
        )
        if date_from is not None
        else None
    )

    end_before = (
        _next_business_day_start(
            date_to,
            company.timezone,
        )
        if date_to is not None
        else None
    )

    opening_transactions: list[
        CashBookTransactionResponse
    ] = []

    if start_at is not None:
        opening_transactions = (
            await _load_active_transactions(
                session,
                company_id=company_id,
                branch_id=branch_id,
                start_at=None,
                end_before=start_at,
                business_today=business_today,
            )
        )

    opening_balance = _net_total(
        opening_transactions
    )

    period_transactions = (
        await _load_active_transactions(
            session,
            company_id=company_id,
            branch_id=branch_id,
            start_at=start_at,
            end_before=end_before,
            business_today=business_today,
        )
    )

    period_transactions.sort(
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.source_type,
            transaction.source_id,
        )
    )

    running_balance = opening_balance

    cash_in = ZERO
    cash_out = ZERO

    for transaction in period_transactions:
        signed_amount = _signed_amount(
            transaction
        )

        if signed_amount > ZERO:
            cash_in = money(
                cash_in
                + signed_amount
            )
        elif signed_amount < ZERO:
            cash_out = money(
                cash_out
                + abs(signed_amount)
            )

        running_balance = money(
            running_balance
            + signed_amount
        )

        transaction.running_balance = (
            running_balance
        )

    closing_balance = money(
        opening_balance
        + cash_in
        - cash_out
    )

    total = len(
        period_transactions
    )

    pages = (
        (
            total
            + page_size
            - 1
        )
        // page_size
        if total
        else 0
    )

    display_transactions = list(
        reversed(
            period_transactions
        )
    )

    start_index = (
        (page - 1)
        * page_size
    )

    end_index = (
        start_index
        + page_size
    )

    page_items = (
        display_transactions[
            start_index:end_index
        ]
    )

    return CashBookListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        summary=CashBookSummaryResponse(
            opening_balance=money(
                opening_balance
            ),
            cash_in=money(
                cash_in
            ),
            cash_out=money(
                cash_out
            ),
            closing_balance=money(
                closing_balance
            ),
            transaction_count=total,
        ),
    )


async def cash_book_summary(
    session: AsyncSession,
    *,
    company_id: int,
    branch_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CashBookSummaryResponse:
    result = await list_cash_book(
        session,
        company_id=company_id,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=1,
    )

    return result.summary
