import pytest
from sqlalchemy import func, select

from app.models import (
    Customer,
    Permission,
    Role,
    UnitOfMeasure,
    User,
    Warehouse,
)


@pytest.mark.asyncio
async def test_seeded_admin_exists(
    db_session,
):
    user_count = await db_session.scalar(
        select(
            func.count(User.id)
        )
    )

    assert user_count >= 1

    admin = await db_session.scalar(
        select(User).where(
            User.username == "admin"
        )
    )

    assert admin is not None
    assert admin.is_active is True
    assert admin.is_superuser is True
    assert admin.role == "super_admin"


@pytest.mark.asyncio
async def test_system_roles_seeded(
    db_session,
):
    role_count = await db_session.scalar(
        select(
            func.count(Role.id)
        )
    )

    assert role_count >= 1

    super_admin_role = await db_session.scalar(
        select(Role).where(
            Role.code == "super_admin"
        )
    )

    assert super_admin_role is not None
    assert super_admin_role.is_active is True


@pytest.mark.asyncio
async def test_system_permissions_seeded(
    db_session,
):
    permission_count = await db_session.scalar(
        select(
            func.count(Permission.id)
        )
    )

    assert permission_count >= 1

    audit_permission = await db_session.scalar(
        select(Permission).where(
            Permission.code == "audit.view"
        )
    )

    assert audit_permission is not None


@pytest.mark.asyncio
async def test_inventory_units_seeded(
    db_session,
):
    rows = (
        await db_session.execute(
            select(
                UnitOfMeasure.code
            )
            .order_by(
                UnitOfMeasure.code
            )
        )
    ).scalars().all()

    codes = set(rows)

    expected = {
        "UNIT",
        "PCS",
        "METER",
        "KG",
        "LITER",
    }

    assert expected.issubset(
        codes
    )


@pytest.mark.asyncio
async def test_inventory_warehouses_seeded(
    db_session,
):
    rows = (
        await db_session.execute(
            select(
                Warehouse.code
            )
            .order_by(
                Warehouse.code
            )
        )
    ).scalars().all()

    codes = set(rows)

    expected = {
        "MAIN",
        "SERVICE",
        "FAULTY",
        "RETURNED",
        "SUP-CLAIM",
    }

    assert expected.issubset(
        codes
    )


@pytest.mark.asyncio
async def test_no_customer_required_at_boot(
    db_session,
):
    customer_count = await db_session.scalar(
        select(
            func.count(Customer.id)
        )
    )

    assert customer_count == 0
