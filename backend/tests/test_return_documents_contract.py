from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RETURN_DOCUMENTS = (
    ROOT
    / "app"
    / "services"
    / "documents"
    / "returns.py"
)

DOCUMENT_API = (
    ROOT
    / "app"
    / "api"
    / "v1"
    / "documents.py"
)

DOCUMENT_EXPORTS = (
    ROOT
    / "app"
    / "services"
    / "documents"
    / "__init__.py"
)


def _read(path: Path) -> str:
    assert path.exists(), f"Missing file: {path}"
    return path.read_text()


def test_refund_acknowledgement_builder_exists():
    text = _read(RETURN_DOCUMENTS)

    assert (
        "async def build_refund_acknowledgement_pdf("
        in text
    )

    assert (
        "RefundStatus.POSTED.value"
        in text
    )

    assert (
        "Refund acknowledgement is available "
        in text
    )
    assert "only for posted refunds" in text


def test_refund_acknowledgement_has_required_content():
    text = _read(RETURN_DOCUMENTS)

    required = [
        "Refund Acknowledgement",
        "Refund Details",
        "Returned Items",
        "Refund Method",
        "Reference",
        "Original Serial",
        "Customer Name",
        "Authorized By",
        "Signature",
        "I acknowledge that I have received",
    ]

    for value in required:
        assert value in text


def test_replacement_issue_builder_exists():
    text = _read(RETURN_DOCUMENTS)

    assert (
        "async def build_replacement_issue_note_pdf("
        in text
    )

    assert (
        "ReturnResolution.REPLACEMENT.value"
        in text
    )

    assert (
        "ReturnStatus.COMPLETED.value"
        in text
    )


def test_replacement_issue_requires_actual_issued_items():
    text = _read(RETURN_DOCUMENTS)

    assert (
        "item.replacement_product_id"
        in text
    )

    assert (
        "item.replacement_stock_movement_id"
        in text
    )

    assert (
        "No issued replacement items exist "
        in text
    )
    assert "for this return" in text


def test_replacement_issue_has_serial_mapping():
    text = _read(RETURN_DOCUMENTS)

    required = [
        "Returned Item / Replacement Item Mapping",
        "Returned Product",
        "Original Serial",
        "Replacement Product",
        "Replacement Serial",
        "replacement_serial_number_id",
        "Customer Name",
        "Signature",
        "Authorized By",
    ]

    for value in required:
        assert value in text


def test_document_api_exposes_refund_pdf():
    text = _read(DOCUMENT_API)

    assert (
        '"/refunds/{refund_id}/acknowledgement/pdf"'
        in text
    )

    assert (
        "download_refund_acknowledgement_pdf"
        in text
    )

    assert (
        "build_refund_acknowledgement_pdf"
        in text
    )


def test_document_api_exposes_replacement_pdf():
    text = _read(DOCUMENT_API)

    assert (
        '"/returns/{return_id}/replacement-issue/pdf"'
        in text
    )

    assert (
        "download_replacement_issue_note_pdf"
        in text
    )

    assert (
        "build_replacement_issue_note_pdf"
        in text
    )


def test_document_package_exports_return_builders():
    text = _read(DOCUMENT_EXPORTS)

    assert (
        "build_refund_acknowledgement_pdf"
        in text
    )

    assert (
        "build_replacement_issue_note_pdf"
        in text
    )
