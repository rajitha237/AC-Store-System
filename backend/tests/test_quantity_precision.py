from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.quantity_precision import (
    quantity_quantum,
    validate_quantity_precision,
)


@pytest.mark.parametrize(
    ("decimal_places", "expected"),
    [
        (0, Decimal("1")),
        (1, Decimal("0.1")),
        (2, Decimal("0.01")),
        (3, Decimal("0.001")),
        (6, Decimal("0.000001")),
    ],
)
def test_quantity_quantum(
    decimal_places: int,
    expected: Decimal,
) -> None:
    assert quantity_quantum(decimal_places) == expected


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1"),
        Decimal("1.0"),
        Decimal("1.000"),
        Decimal("27"),
        Decimal("27.000"),
    ],
)
def test_whole_unit_quantity_accepts_integer_values(
    value: Decimal,
) -> None:
    result = validate_quantity_precision(
        value,
        decimal_places=0,
    )

    assert result == value
    assert result == result.to_integral_value()


@pytest.mark.parametrize(
    "value",
    [
        Decimal("0.001"),
        Decimal("1.5"),
        Decimal("26.999"),
        Decimal("27.001"),
    ],
)
def test_whole_unit_quantity_rejects_fractional_values(
    value: Decimal,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_quantity_precision(
            value,
            decimal_places=0,
        )

    assert exc_info.value.status_code == 422
    assert "whole number" in exc_info.value.detail


def test_meter_quantity_accepts_two_decimal_places() -> None:
    result = validate_quantity_precision(
        Decimal("12.25"),
        decimal_places=2,
    )

    assert result == Decimal("12.25")


def test_meter_quantity_rejects_three_decimal_places() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_quantity_precision(
            Decimal("12.251"),
            decimal_places=2,
        )

    assert exc_info.value.status_code == 422
    assert "at most 2 decimal places" in (
        exc_info.value.detail
    )


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1.001"),
        Decimal("2.125"),
        Decimal("10.999"),
    ],
)
def test_three_decimal_unit_accepts_valid_values(
    value: Decimal,
) -> None:
    assert (
        validate_quantity_precision(
            value,
            decimal_places=3,
        )
        == value
    )


def test_quantity_rejects_negative_value() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_quantity_precision(
            Decimal("-1"),
            decimal_places=0,
        )

    assert exc_info.value.status_code == 422


def test_quantity_rejects_zero_by_default() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_quantity_precision(
            Decimal("0"),
            decimal_places=0,
        )

    assert exc_info.value.status_code == 422


def test_quantity_can_allow_zero_explicitly() -> None:
    result = validate_quantity_precision(
        Decimal("0"),
        decimal_places=0,
        allow_zero=True,
    )

    assert result == Decimal("0")


@pytest.mark.parametrize(
    "decimal_places",
    [-1, 7],
)
def test_invalid_unit_precision_rejected(
    decimal_places: int,
) -> None:
    with pytest.raises(ValueError):
        quantity_quantum(decimal_places)
