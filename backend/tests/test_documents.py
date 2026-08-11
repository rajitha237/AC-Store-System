import uuid

import pytest

from app.core.security import (
    create_access_token,
    hash_password,
)
from app.models import User

from tests.test_sales_payments import (
    confirm_invoice,
    create_sales_fixture,
)


async def create_document_test_user(
    db_session,
    *,
    role: str,
) -> User:
    unique = uuid.uuid4().hex[:12]

    user = User(
        username=f"documents_{unique}",
        email=f"documents_{unique}@test.local",
        full_name=f"Documents Test {unique}",
        hashed_password=hash_password(
            "Test@12345"
        ),
        role=role,
        is_active=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


def headers_for_user(
    user: User,
) -> dict[str, str]:
    token = create_access_token(
        subject=str(user.id)
    )

    return {
        "Authorization":
            f"Bearer {token}",
    }


@pytest.mark.asyncio
async def test_sales_invoice_pdf_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/documents/sales-invoices/1/pdf"
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_payment_receipt_pdf_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/documents/payment-receipts/1/pdf"
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sales_invoice_pdf_rejects_user_without_permission(
    client,
    db_session,
):
    user = await create_document_test_user(
        db_session,
        role="technician",
    )

    response = await client.get(
        "/api/v1/documents/sales-invoices/1/pdf",
        headers=headers_for_user(user),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Permission required: sales.view"
    )


@pytest.mark.asyncio
async def test_payment_receipt_pdf_rejects_user_without_permission(
    client,
    db_session,
):
    user = await create_document_test_user(
        db_session,
        role="technician",
    )

    response = await client.get(
        "/api/v1/documents/payment-receipts/1/pdf",
        headers=headers_for_user(user),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Permission required: payments.view"
    )


@pytest.mark.asyncio
async def test_missing_sales_invoice_pdf_returns_404(
    client,
    admin_headers,
):
    response = await client.get(
        (
            "/api/v1/documents/"
            "sales-invoices/999999999/pdf"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_missing_payment_receipt_pdf_returns_404(
    client,
    admin_headers,
):
    response = await client.get(
        (
            "/api/v1/documents/"
            "payment-receipts/999999999/pdf"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sales_invoice_pdf_download_contract(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="501",
        quantity="1.000",
        unit_price="1500.00",
    )

    invoice = fixture["invoice"]

    confirm_response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
    )

    assert confirm_response.status_code == 200, (
        confirm_response.text
    )

    confirmed = confirm_response.json()

    response = await client.get(
        (
            "/api/v1/documents/"
            f"sales-invoices/{invoice['id']}/pdf"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    assert (
        response.headers["content-type"]
        == "application/pdf"
    )

    disposition = response.headers.get(
        "content-disposition",
        "",
    )

    assert "attachment" in disposition.lower()

    assert (
        f'{confirmed["invoice_number"]}.pdf'
        in disposition
    )

    assert response.content.startswith(
        b"%PDF"
    )

    assert len(response.content) > 100


@pytest.mark.asyncio
async def test_payment_receipt_pdf_download_contract(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_sales_fixture(
        client,
        admin_headers,
        db_session,
        suffix="502",
        quantity="1.000",
        unit_price="1750.00",
    )

    invoice = fixture["invoice"]

    confirm_response = await confirm_invoice(
        client,
        admin_headers,
        invoice["id"],
        initial_payment={
            "amount": "500.00",
            "payment_method": "cash",
            "reference_number":
                "DOC-PDF-PAYMENT",
            "notes":
                "Document PDF integration test",
        },
    )

    assert confirm_response.status_code == 200, (
        confirm_response.text
    )

    confirmed = confirm_response.json()

    payments = confirmed.get(
        "payments",
        [],
    )

    assert payments

    payment = payments[0]

    assert payment["id"] >= 1
    assert payment["receipt_number"]

    response = await client.get(
        (
            "/api/v1/documents/"
            f"payment-receipts/{payment['id']}/pdf"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    assert (
        response.headers["content-type"]
        == "application/pdf"
    )

    disposition = response.headers.get(
        "content-disposition",
        "",
    )

    assert "attachment" in disposition.lower()

    assert (
        f'{payment["receipt_number"]}.pdf'
        in disposition
    )

    assert response.content.startswith(
        b"%PDF"
    )

    assert len(response.content) > 100


def test_document_openapi_contract(
    client,
):
    schema = client._transport.app.openapi()

    invoice_operation = (
        schema["paths"][
            (
                "/api/v1/documents/"
                "sales-invoices/{invoice_id}/pdf"
            )
        ]["get"]
    )

    receipt_operation = (
        schema["paths"][
            (
                "/api/v1/documents/"
                "payment-receipts/{payment_id}/pdf"
            )
        ]["get"]
    )

    for operation in (
        invoice_operation,
        receipt_operation,
    ):
        assert operation["security"] == [
            {
                "OAuth2PasswordBearer": []
            }
        ]

        content = (
            operation["responses"]
            ["200"]
            ["content"]
        )

        assert "application/pdf" in content
        assert "application/json" not in content
