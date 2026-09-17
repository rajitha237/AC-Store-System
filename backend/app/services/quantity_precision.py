from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, UnitOfMeasure


def decimal_value(value: Any) -> Decimal:
    """
    Convert a quantity value to Decimal without introducing
    binary floating-point artifacts.
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantity must be a valid decimal number",
        ) from exc


def quantity_quantum(decimal_places: int) -> Decimal:
    """
    Return the smallest valid quantity increment for a unit.

    Examples:
        0 -> Decimal("1")
        2 -> Decimal("0.01")
        3 -> Decimal("0.001")
    """
    if decimal_places < 0 or decimal_places > 6:
        raise ValueError(
            "Unit decimal_places must be between 0 and 6"
        )

    return Decimal(1).scaleb(-decimal_places)


def validate_quantity_precision(
    value: Any,
    *,
    decimal_places: int,
    field_name: str = "Quantity",
    allow_zero: bool = False,
) -> Decimal:
    """
    Validate a quantity against the unit-of-measure precision.

    This function NEVER silently rounds an invalid quantity.

    UNIT / PCS with decimal_places=0:
        1      -> valid
        2.000  -> valid
        1.5    -> rejected
        26.999 -> rejected

    METER with decimal_places=2:
        1.25   -> valid
        1.234  -> rejected

    KG / LITER with decimal_places=3:
        1.125  -> valid
    """
    quantity = decimal_value(value)

    if quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} cannot be negative",
        )

    if not allow_zero and quantity == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be greater than zero",
        )

    quantum = quantity_quantum(decimal_places)

    normalized = quantity.quantize(quantum)

    if quantity != normalized:
        if decimal_places == 0:
            precision_message = "a whole number"
        elif decimal_places == 1:
            precision_message = "at most 1 decimal place"
        else:
            precision_message = (
                f"at most {decimal_places} decimal places"
            )

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"{field_name} must use {precision_message}"
            ),
        )

    return normalized


async def validate_product_quantity(
    session: AsyncSession,
    *,
    product: Product,
    value: Any,
    field_name: str = "Quantity",
    allow_zero: bool = False,
) -> Decimal:
    """
    Validate quantity using the Product's UnitOfMeasure contract.
    """
    unit = await session.get(
        UnitOfMeasure,
        product.unit_id,
    )

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{product.product_code}: "
                "unit of measure was not found"
            ),
        )

    if not unit.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{product.product_code}: "
                "unit of measure is inactive"
            ),
        )

    return validate_quantity_precision(
        value,
        decimal_places=unit.decimal_places,
        field_name=field_name,
        allow_zero=allow_zero,
    )
