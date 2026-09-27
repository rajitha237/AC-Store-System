from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.cash_book import (
    CashBookDailyApproval,
)
from app.services.cash_book import (
    ensure_cash_book_day_not_approved,
)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, approval):
        self.approval = approval

    async def execute(self, _statement):
        return _ScalarResult(
            self.approval
        )


@pytest.mark.asyncio
async def test_unapproved_day_allows_manual_change():
    session = _Session(None)

    await ensure_cash_book_day_not_approved(
        session,
        company_id=1,
        business_date=date(
            2026,
            9,
            27,
        ),
    )


@pytest.mark.asyncio
async def test_approved_day_blocks_manual_change():
    approval = CashBookDailyApproval(
        id=1,
        company_id=1,
        business_date=date(
            2026,
            9,
            27,
        ),
        opening_balance=Decimal(
            "100.00"
        ),
        cash_in=Decimal(
            "50.00"
        ),
        cash_out=Decimal(
            "20.00"
        ),
        closing_balance=Decimal(
            "130.00"
        ),
        transaction_count=2,
        approved_by_id=2,
    )

    session = _Session(
        approval
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        await ensure_cash_book_day_not_approved(
            session,
            company_id=1,
            business_date=date(
                2026,
                9,
                27,
            ),
        )

    assert exc.value.status_code == 409
    assert (
        "already been approved"
        in str(exc.value.detail)
    )
