from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (
        ROOT / relative_path
    ).read_text()


def test_returnable_schema_exposes_serial_identity():
    source = read(
        "backend/app/schemas/returns.py"
    )

    assert (
        "serial_number_id: int | None = None"
        in source
    )
    assert (
        "serial_number: str | None = None"
        in source
    )


def test_returnable_service_hydrates_serial_identity():
    source = read(
        "backend/app/services/returns.py"
    )

    assert (
        "serial_record = await session.get("
        in source
    )
    assert (
        "invoice_item.serial_number_id"
        in source
    )
    assert (
        "serial_number=serial_number"
        in source
    )


def test_returns_frontend_prefers_eligibility_serial():
    source = read(
        "frontend/src/app/returns/page.tsx"
    )

    assert (
        "eligibilityItem\n"
        "                                      ?.serial_number"
        in source
    )
    assert (
        "eligibilityItem\n"
        "                                            "
        "?.serial_number_id"
        in source
    )


def test_return_detail_schema_exposes_serial_text():
    source = read(
        "backend/app/schemas/returns.py"
    )

    detail_start = source.index(
        "class SalesReturnItemResponse"
    )
    detail_end = source.index(
        "class SalesReturnResponse"
    )

    detail_schema = source[
        detail_start:detail_end
    ]

    assert (
        "serial_number: str | None = None"
        in detail_schema
    )


def test_return_detail_builder_hydrates_serial_text():
    source = read(
        "backend/app/services/returns.py"
    )

    start = source.index(
        "async def build_return_detail("
    )

    detail_builder = source[start:]

    assert "item_responses" in detail_builder
    assert (
        "serial_number=serial_number"
        in detail_builder
    )
    assert "items=item_responses" in detail_builder


def test_return_details_ui_shows_original_serial():
    source = read(
        "frontend/src/app/returns/page.tsx"
    )

    assert "item.serial_number && (" in source
    assert "{item.serial_number}" in source
    assert '" — Serial: "' in source



def test_frontend_return_type_has_serial_identity():
    source = read(
        "frontend/src/types/returns.ts"
    )

    assert "serial_number_id:" in source
    assert "serial_number:" in source
