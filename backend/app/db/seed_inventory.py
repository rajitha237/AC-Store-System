from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Branch,
    UnitOfMeasure,
    Warehouse,
    WarehouseType,
)


DEFAULT_UNITS: tuple[tuple[str, str, int], ...] = (
    ("UNIT", "Unit", 0),
    ("PCS", "Pieces", 0),
    ("METER", "Meter", 2),
    ("KG", "Kilogram", 3),
    ("LITER", "Liter", 3),
)


DEFAULT_WAREHOUSES: tuple[
    tuple[str, str, str], ...
] = (
    (
        "MAIN",
        "Main Stock",
        WarehouseType.MAIN.value,
    ),
    (
        "SERVICE",
        "Service Stock",
        WarehouseType.SERVICE.value,
    ),
    (
        "FAULTY",
        "Faulty Stock",
        WarehouseType.FAULTY.value,
    ),
    (
        "RETURNED",
        "Returned Stock",
        WarehouseType.RETURNED.value,
    ),
    (
        "SUP-CLAIM",
        "Supplier Claim Stock",
        WarehouseType.SUPPLIER_CLAIM.value,
    ),
)


async def seed_units(
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(UnitOfMeasure)
    )
    existing = {
        unit.code: unit
        for unit in result.scalars().all()
    }

    for code, name, decimal_places in DEFAULT_UNITS:
        unit = existing.get(code)

        if unit is None:
            session.add(
                UnitOfMeasure(
                    code=code,
                    name=name,
                    decimal_places=decimal_places,
                    is_active=True,
                )
            )
        else:
            unit.name = name
            unit.decimal_places = decimal_places
            unit.is_active = True


async def seed_warehouses(
    session: AsyncSession,
) -> None:
    branch_result = await session.execute(
        select(Branch)
        .where(
            Branch.is_main_branch.is_(True),
            Branch.is_active.is_(True),
        )
        .order_by(Branch.id)
    )
    branch = branch_result.scalars().first()

    if branch is None:
        return

    warehouse_result = await session.execute(
        select(Warehouse).where(
            Warehouse.branch_id == branch.id
        )
    )

    existing = {
        warehouse.code: warehouse
        for warehouse in warehouse_result.scalars().all()
    }

    for code, name, warehouse_type in DEFAULT_WAREHOUSES:
        warehouse = existing.get(code)

        if warehouse is None:
            session.add(
                Warehouse(
                    branch_id=branch.id,
                    code=code,
                    name=name,
                    warehouse_type=warehouse_type,
                    is_active=True,
                )
            )
        else:
            warehouse.name = name
            warehouse.warehouse_type = warehouse_type
            warehouse.is_active = True


async def seed_inventory_data(
    session: AsyncSession,
) -> None:
    await seed_units(session)
    await seed_warehouses(session)
    await session.commit()
