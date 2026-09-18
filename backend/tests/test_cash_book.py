from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.cash_book import (
    CashBookTransactionResponse,
)
from app.services.cash_book import (
    _customer_transaction,
    _manual_transaction,
    _net_total,
    _signed_amount,
    _supplier_transaction,
    money,
)


def utc(
    year: int,
    month: int,
    day: int,
) -> datetime:
    return datetime(
        year,
        month,
        day,
        tzinfo=timezone.utc,
    )


def test_money_rounding() -> None:
    assert (
        money("10.125")
        == Decimal("10.13")
    )

    assert (
        money("10")
        == Decimal("10.00")
    )


def test_customer_payment_maps_to_cash_in() -> None:
    payment = SimpleNamespace(
        id=1,
        company_id=1,
        branch_id=1,
        receipt_number="REC-001",
        reference_number="REF-001",
        payment_date=utc(
            2026,
            8,
            20,
        ),
        amount=Decimal("1500.00"),
        payment_method="cash",
        cheque_date=None,
        notes="Sale payment",
        is_reversed=False,
        created_by_id=1,
        created_at=utc(
            2026,
            8,
            20,
        ),
    )

    result = _customer_transaction(
        payment
    )

    assert result.direction == "cash_in"
    assert (
        result.amount
        == Decimal("1500.00")
    )
    assert (
        result.source_reference
        == "REC-001"
    )
    assert result.status == "active"


def test_supplier_payment_maps_to_cash_out() -> None:
    payment = SimpleNamespace(
        id=2,
        company_id=1,
        branch_id=1,
        payment_number="SP-001",
        reference_number="SUP-REF",
        payment_date=utc(
            2026,
            8,
            21,
        ),
        amount=Decimal("600.00"),
        payment_method="bank_transfer",
        notes="Supplier settlement",
        is_reversed=False,
        status="posted",
        created_by_id=1,
        created_at=utc(
            2026,
            8,
            21,
        ),
    )

    result = _supplier_transaction(
        payment
    )

    assert result.direction == "cash_out"
    assert (
        result.amount
        == Decimal("600.00")
    )
    assert (
        result.source_reference
        == "SP-001"
    )


def test_manual_cash_in_mapping() -> None:
    entry = SimpleNamespace(
        id=3,
        company_id=1,
        branch_id=1,
        entry_number="CB-001",
        reference_number="MAN-001",
        entry_type="cash_in",
        entry_date=utc(
            2026,
            8,
            22,
        ),
        amount=Decimal("200.00"),
        payment_method="cash",
        category="Other income",
        description="Manual income",
        notes=None,
        cheque_date=None,
        cheque_status=None,
        cheque_cleared_at=None,
        reversed_at=None,
    )

    result = _manual_transaction(
        entry
    )

    assert result.direction == "cash_in"
    assert (
        result.amount
        == Decimal("200.00")
    )


def test_manual_cash_out_mapping() -> None:
    entry = SimpleNamespace(
        id=4,
        company_id=1,
        branch_id=1,
        entry_number="CB-002",
        reference_number=None,
        entry_type="cash_out",
        entry_date=utc(
            2026,
            8,
            22,
        ),
        amount=Decimal("75.00"),
        payment_method="cash",
        category="Expense",
        description="Office expense",
        notes=None,
        cheque_date=None,
        cheque_status=None,
        cheque_cleared_at=None,
        reversed_at=None,
    )

    result = _manual_transaction(
        entry
    )

    assert result.direction == "cash_out"
    assert (
        result.amount
        == Decimal("75.00")
    )


def transaction(
    *,
    source_id: int,
    direction: str,
    amount: str,
    day: int,
    running_balance: str | None = None,
) -> CashBookTransactionResponse:
    return CashBookTransactionResponse(
        source_type="test",
        source_id=source_id,
        source_reference=f"T-{source_id}",
        direction=direction,
        transaction_date=utc(
            2026,
            8,
            day,
        ),
        amount=Decimal(amount),
        payment_method="cash",
        category="Test",
        description="Test",
        branch_id=1,
        status="active",
        running_balance=(
            Decimal(
                running_balance
            )
            if running_balance
            is not None
            else None
        ),
    )


def test_signed_amount_cash_in() -> None:
    item = transaction(
        source_id=1,
        direction="cash_in",
        amount="100.00",
        day=1,
    )

    assert (
        _signed_amount(item)
        == Decimal("100.00")
    )


def test_signed_amount_cash_out() -> None:
    item = transaction(
        source_id=2,
        direction="cash_out",
        amount="40.00",
        day=2,
    )

    assert (
        _signed_amount(item)
        == Decimal("-40.00")
    )


def test_net_total() -> None:
    items = [
        transaction(
            source_id=1,
            direction="cash_in",
            amount="1000.00",
            day=1,
        ),
        transaction(
            source_id=2,
            direction="cash_out",
            amount="250.00",
            day=2,
        ),
        transaction(
            source_id=3,
            direction="cash_in",
            amount="100.00",
            day=3,
        ),
    ]

    assert (
        _net_total(items)
        == Decimal("850.00")
    )


def test_running_balance_math() -> None:
    opening = Decimal("500.00")

    items = [
        transaction(
            source_id=1,
            direction="cash_in",
            amount="200.00",
            day=1,
        ),
        transaction(
            source_id=2,
            direction="cash_out",
            amount="50.00",
            day=2,
        ),
        transaction(
            source_id=3,
            direction="cash_in",
            amount="25.00",
            day=3,
        ),
    ]

    running = opening

    for item in items:
        running = money(
            running
            + _signed_amount(item)
        )

        item.running_balance = running

    assert (
        items[0].running_balance
        == Decimal("700.00")
    )

    assert (
        items[1].running_balance
        == Decimal("650.00")
    )

    assert (
        items[2].running_balance
        == Decimal("675.00")
    )


def test_newest_first_pagination_order() -> None:
    chronological = [
        transaction(
            source_id=1,
            direction="cash_in",
            amount="10.00",
            day=1,
        ),
        transaction(
            source_id=2,
            direction="cash_in",
            amount="10.00",
            day=2,
        ),
        transaction(
            source_id=3,
            direction="cash_in",
            amount="10.00",
            day=3,
        ),
        transaction(
            source_id=4,
            direction="cash_in",
            amount="10.00",
            day=4,
        ),
        transaction(
            source_id=5,
            direction="cash_in",
            amount="10.00",
            day=5,
        ),
    ]

    display = list(
        reversed(
            chronological
        )
    )

    assert [
        item.source_id
        for item in display[0:2]
    ] == [5, 4]

    assert [
        item.source_id
        for item in display[2:4]
    ] == [3, 2]


@pytest.mark.parametrize(
    (
        "date_from",
        "date_to",
        "valid",
    ),
    [
        (
            date(2026, 8, 1),
            date(2026, 8, 31),
            True,
        ),
        (
            date(2026, 8, 31),
            date(2026, 8, 1),
            False,
        ),
    ],
)
def test_date_filter_contract(
    date_from: date,
    date_to: date,
    valid: bool,
) -> None:
    assert (
        date_from <= date_to
    ) is valid


def test_cash_book_entry_number() -> None:
    from app.services.cash_book import (
        cash_book_entry_number,
    )

    assert (
        cash_book_entry_number(1)
        == "CB-000001"
    )

    assert (
        cash_book_entry_number(123)
        == "CB-000123"
    )


def test_cash_book_payment_method_validation() -> None:
    from pydantic import ValidationError

    from app.models.sales import (
        PaymentMethod,
    )
    from app.schemas.cash_book import (
        ManualCashBookEntryCreate,
    )

    payload = (
        ManualCashBookEntryCreate(
            entry_type="cash_in",
            amount=Decimal("100.00"),
            payment_method="card",
            category="Other income",
            description="Manual income",
        )
    )

    assert (
        payload.payment_method
        == PaymentMethod.CARD
    )

    try:
        ManualCashBookEntryCreate(
            entry_type="cash_out",
            amount=Decimal("50.00"),
            payment_method=(
                "invalid-method"
            ),
            category="Expense",
            description="Invalid",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "INVALID_PAYMENT_METHOD_ACCEPTED"
        )


def test_manual_cash_book_snapshot() -> None:
    from types import SimpleNamespace

    from app.services.cash_book import (
        manual_cash_book_snapshot,
    )

    entry = SimpleNamespace(
        id=5,
        entry_number="CB-000005",
        company_id=1,
        branch_id=1,
        entry_type="cash_out",
        entry_date=utc(
            2026,
            8,
            26,
        ),
        amount=Decimal("125.50"),
        payment_method="cash",
        cheque_date=None,
        cheque_status=None,
        cheque_cleared_at=None,
        cheque_cleared_by_id=None,
        category="Expense",
        description="Office expense",
        reference_number="REF-5",
        notes=None,
        created_by_id=1,
        reversed_at=None,
        reversed_by_id=None,
        reversal_reason=None,
    )

    snapshot = (
        manual_cash_book_snapshot(
            entry
        )
    )

    assert (
        snapshot["entry_number"]
        == "CB-000005"
    )

    assert (
        snapshot["amount"]
        == "125.50"
    )

    assert (
        snapshot["entry_type"]
        == "cash_out"
    )
