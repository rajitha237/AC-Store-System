from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.cash_book import (
    _business_day_start,
    _business_today,
    _customer_transaction,
    _manual_transaction,
    _next_business_day_start,
    _signed_amount,
)


def manual_cheque(
    *,
    cheque_date: date,
    cheque_status: str = "pending",
    reversed_at=None,
):
    return SimpleNamespace(
        id=101,
        company_id=1,
        branch_id=1,
        entry_number="CB-000101",
        reference_number="CHQ-101",
        entry_type="cash_out",
        entry_date=datetime(
            2026,
            9,
            18,
            3,
            30,
            tzinfo=timezone.utc,
        ),
        amount=Decimal("25000.00"),
        payment_method="cheque",
        category="Operating Expense",
        description="Issued cheque",
        notes=None,
        cheque_date=cheque_date,
        cheque_status=cheque_status,
        cheque_cleared_at=(
            datetime(
                2026,
                9,
                18,
                4,
                0,
                tzinfo=timezone.utc,
            )
            if cheque_status == "cleared"
            else None
        ),
        reversed_at=reversed_at,
    )


def test_future_issued_cheque_has_zero_cash_effect():
    entry = manual_cheque(
        cheque_date=date(2026, 9, 20),
    )

    transaction = _manual_transaction(
        entry,
        business_today=date(2026, 9, 18),
    )

    assert transaction.status == "pending_cheque"
    assert transaction.can_confirm_cheque is False
    assert transaction.can_edit is True
    assert transaction.can_delete is True

    assert _signed_amount(
        transaction
    ) == Decimal("0.00")


def test_due_issued_cheque_can_be_confirmed():
    entry = manual_cheque(
        cheque_date=date(2026, 9, 18),
    )

    transaction = _manual_transaction(
        entry,
        business_today=date(2026, 9, 18),
    )

    assert transaction.status == "pending_cheque"
    assert transaction.can_confirm_cheque is True

    assert _signed_amount(
        transaction
    ) == Decimal("0.00")


def test_past_due_issued_cheque_can_be_confirmed():
    entry = manual_cheque(
        cheque_date=date(2026, 9, 17),
    )

    transaction = _manual_transaction(
        entry,
        business_today=date(2026, 9, 18),
    )

    assert transaction.can_confirm_cheque is True

    assert _signed_amount(
        transaction
    ) == Decimal("0.00")


def test_cleared_issued_cheque_reduces_cash():
    entry = manual_cheque(
        cheque_date=date(2026, 9, 18),
        cheque_status="cleared",
    )

    transaction = _manual_transaction(
        entry,
        business_today=date(2026, 9, 18),
    )

    assert transaction.status == "active"
    assert transaction.can_confirm_cheque is False
    assert transaction.can_edit is False
    assert transaction.can_delete is True

    assert _signed_amount(
        transaction
    ) == Decimal("-25000.00")


def test_reversed_cheque_has_no_cash_effect():
    entry = manual_cheque(
        cheque_date=date(2026, 9, 18),
        cheque_status="cleared",
        reversed_at=datetime(
            2026,
            9,
            19,
            tzinfo=timezone.utc,
        ),
    )

    transaction = _manual_transaction(
        entry,
        business_today=date(2026, 9, 19),
    )

    assert transaction.status == "reversed"
    assert transaction.can_confirm_cheque is False
    assert transaction.can_edit is False
    assert transaction.can_delete is False

    assert _signed_amount(
        transaction
    ) == Decimal("0.00")


def test_colombo_business_day_boundaries():
    start = _business_day_start(
        date(2026, 9, 18),
        "Asia/Colombo",
    )

    end = _next_business_day_start(
        date(2026, 9, 18),
        "Asia/Colombo",
    )

    assert start == datetime(
        2026,
        9,
        17,
        18,
        30,
        tzinfo=timezone.utc,
    )

    assert end == datetime(
        2026,
        9,
        18,
        18,
        30,
        tzinfo=timezone.utc,
    )


def test_business_today_returns_date():
    result = _business_today(
        "Asia/Colombo"
    )

    assert isinstance(
        result,
        date,
    )


def test_customer_cheque_exposes_cheque_date():
    payment = SimpleNamespace(
        id=501,
        company_id=1,
        branch_id=1,
        receipt_number="RCPT-501",
        reference_number="CUST-CHQ-501",
        payment_date=datetime(
            2026,
            9,
            18,
            5,
            0,
            tzinfo=timezone.utc,
        ),
        amount=Decimal("15000.00"),
        payment_method="cheque",
        cheque_date=date(
            2026,
            9,
            25,
        ),
        notes="Customer cheque",
        is_reversed=False,
        created_by_id=1,
        created_at=datetime(
            2026,
            9,
            18,
            5,
            0,
            tzinfo=timezone.utc,
        ),
    )

    transaction = _customer_transaction(
        payment
    )

    assert transaction.direction == "cash_in"
    assert transaction.payment_method == "cheque"
    assert transaction.cheque_date == date(
        2026,
        9,
        25,
    )
    assert transaction.can_edit is False
    assert transaction.can_delete is False
