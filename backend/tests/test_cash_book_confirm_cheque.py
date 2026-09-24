from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditLog, User
from app.models.cash_book import ManualCashBookEntry


@pytest.mark.asyncio
async def test_confirm_due_manual_cheque_end_to_end(
    client,
    admin_headers,
    db_session,
):
    create_response = await client.post(
        "/api/v1/cash-book/manual",
        headers=admin_headers,
        json={
            "entry_type": "cash_out",
            "entry_date": date.today().isoformat(),
            "amount": "25000.00",
            "payment_method": "cheque",
            "category": "Integration Test Expense",
            "description": "Confirm cheque integration test",
            "reference_number": "TEST-CHQ-CONFIRM-001",
            "cheque_date": date.today().isoformat(),
            "notes": "Pending cheque before confirmation",
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    created = create_response.json()

    assert created["cheque_status"] == "pending"
    assert created["cheque_cleared_at"] is None
    assert created["cheque_cleared_by_id"] is None

    entry_id = created["id"]

    confirm_response = await client.post(
        (
            f"/api/v1/cash-book/manual/"
            f"{entry_id}/confirm-cheque"
        ),
        headers=admin_headers,
        json={
            "notes": "Confirmed by integration test",
        },
    )

    assert confirm_response.status_code == 200, (
        confirm_response.text
    )

    confirmed = confirm_response.json()

    assert confirmed["id"] == entry_id
    assert confirmed["cheque_status"] == "cleared"
    assert confirmed["cheque_cleared_at"] is not None
    assert confirmed["cheque_cleared_by_id"] is not None

    db_session.expire_all()

    entry = (
        await db_session.execute(
            select(ManualCashBookEntry)
            .where(
                ManualCashBookEntry.id == entry_id
            )
        )
    ).scalar_one()

    assert entry.cheque_status == "cleared"
    assert entry.cheque_cleared_at is not None
    assert entry.cheque_cleared_by_id is not None
    assert entry.amount == Decimal("25000.00")

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(
                AuditLog.action
                == "cash_book.cheque_cleared",
                AuditLog.entity_type
                == "manual_cash_book_entry",
                AuditLog.entity_id
                == entry_id,
            )
            .order_by(AuditLog.id.desc())
        )
    ).scalars().first()

    assert audit is not None
    assert audit.entity_reference == created["entry_number"]


@pytest.mark.asyncio
async def test_confirm_manual_cheque_is_idempotency_protected(
    client,
    admin_headers,
):
    create_response = await client.post(
        "/api/v1/cash-book/manual",
        headers=admin_headers,
        json={
            "entry_type": "cash_out",
            "entry_date": date.today().isoformat(),
            "amount": "1000.00",
            "payment_method": "cheque",
            "category": "Integration Test Expense",
            "description": "Duplicate confirmation protection",
            "reference_number": "TEST-CHQ-CONFIRM-002",
            "cheque_date": date.today().isoformat(),
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    entry_id = create_response.json()["id"]

    first = await client.post(
        (
            f"/api/v1/cash-book/manual/"
            f"{entry_id}/confirm-cheque"
        ),
        headers=admin_headers,
        json={},
    )

    assert first.status_code == 200, first.text
    assert first.json()["cheque_status"] == "cleared"

    second = await client.post(
        (
            f"/api/v1/cash-book/manual/"
            f"{entry_id}/confirm-cheque"
        ),
        headers=admin_headers,
        json={},
    )

    assert second.status_code == 409, second.text
    assert (
        second.json()["detail"]
        == "Cheque is already confirmed paid"
    )


async def _cash_book_headers_for_role(
    db_session,
    role: str,
) -> dict[str, str]:
    user = User(
        username=f"cashbook_{role}_test",
        email=f"cashbook_{role}_test@test.local",
        full_name=f"Cash Book {role.title()} Test",
        hashed_password=hash_password("Test@12345"),
        role=role,
        is_active=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(subject=str(user.id))

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    ["owner", "accountant"],
)
async def test_owner_and_accountant_can_confirm_due_cheque(
    client,
    db_session,
    role,
):
    headers = await _cash_book_headers_for_role(
        db_session,
        role,
    )

    create_response = await client.post(
        "/api/v1/cash-book/manual",
        headers=headers,
        json={
            "entry_type": "cash_out",
            "entry_date": date.today().isoformat(),
            "amount": "1234.00",
            "payment_method": "cheque",
            "category": "Role Permission Test",
            "description": (
                f"Cheque confirmation by {role}"
            ),
            "reference_number": (
                f"ROLE-CHQ-{role.upper()}"
            ),
            "cheque_date": date.today().isoformat(),
        },
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    entry_id = create_response.json()["id"]

    response = await client.post(
        (
            f"/api/v1/cash-book/manual/"
            f"{entry_id}/confirm-cheque"
        ),
        headers=headers,
        json={},
    )

    assert response.status_code == 200, (
        f"{role}: {response.text}"
    )
    assert response.json()["cheque_status"] == "cleared"
