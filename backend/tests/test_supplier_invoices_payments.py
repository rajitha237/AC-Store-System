from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import (
    Supplier,
    SupplierInvoice,
    SupplierPayment,
)
from app.services.purchasing import supplier_invoice_aging
from tests.test_goods_receipts import (
    approve_po,
)
from tests.test_purchase_orders import (
    create_po_fixture,
)


BASE_URL = "/api/v1/purchase-orders"


def dec(value) -> Decimal:
    return Decimal(str(value))


@pytest.mark.asyncio
async def test_supplier_invoice_increases_payable(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="981",
        quantity="2.000",
        unit_cost="1000.00",
        discount="0.00",
        tax="0.00",
    )

    po = fixture["purchase_order"]

    await approve_po(
        client,
        admin_headers,
        po["id"],
    )

    grn = await client.post(
        f"{BASE_URL}/{po['id']}/receive",
        headers=admin_headers,
        json={
            "items": [
                {
                    "purchase_order_item_id":
                        po["items"][0]["id"],
                    "quantity":
                        "2.000",
                }
            ]
        },
    )

    assert grn.status_code == 201

    grn_data = grn.json()

    response = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "purchase_order_id":
                po["id"],
            "goods_receipt_id":
                grn_data["id"],
            "supplier_invoice_number":
                "SUP-INV-981",
            "subtotal":
                "2000.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    data = response.json()

    assert data["invoice_number"].startswith(
        "PINV-"
    )

    assert data["status"] == "posted"

    assert dec(
        data["balance_amount"]
    ) == Decimal("2000.00")

    supplier = await db_session.get(
        Supplier,
        fixture["supplier"]["id"],
    )

    assert dec(
        supplier.current_payable
    ) == Decimal("2000.00")


@pytest.mark.asyncio
async def test_supplier_payment_reduces_payable_and_invoice_balance(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="982",
        quantity="1.000",
        unit_cost="1500.00",
        discount="0.00",
        tax="0.00",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-982",
            "subtotal":
                "1500.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert invoice.status_code == 201

    invoice_data = invoice.json()

    payment = await client.post(
        f"{BASE_URL}/supplier-payments",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_id":
                invoice_data["id"],
            "amount":
                "500.00",
            "payment_method":
                "cash",
        },
    )

    assert payment.status_code == 201, (
        payment.text
    )

    invoice_detail = await client.get(
        (
            f"{BASE_URL}/supplier-invoices/"
            f"{invoice_data['id']}"
        ),
        headers=admin_headers,
    )

    updated = invoice_detail.json()

    assert dec(
        updated["paid_amount"]
    ) == Decimal("500.00")

    assert dec(
        updated["balance_amount"]
    ) == Decimal("1000.00")

    supplier = await db_session.get(
        Supplier,
        supplier_id,
    )

    assert dec(
        supplier.current_payable
    ) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_full_payment_marks_invoice_paid(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="983",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-983",
            "subtotal":
                "1000.00",
        },
    )

    assert invoice.status_code == 201

    invoice_data = invoice.json()

    payment = await client.post(
        f"{BASE_URL}/supplier-payments",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_id":
                invoice_data["id"],
            "amount":
                "1000.00",
            "payment_method":
                "bank_transfer",
            "reference_number":
                "TX-983",
        },
    )

    assert payment.status_code == 201

    detail = await client.get(
        (
            f"{BASE_URL}/supplier-invoices/"
            f"{invoice_data['id']}"
        ),
        headers=admin_headers,
    )

    data = detail.json()

    assert data["status"] == "paid"

    assert dec(
        data["balance_amount"]
    ) == Decimal("0.00")


@pytest.mark.asyncio
async def test_payment_reversal_restores_payable_and_invoice_balance(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="984",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-984",
            "subtotal":
                "900.00",
        },
    )

    invoice_data = invoice.json()

    payment = await client.post(
        f"{BASE_URL}/supplier-payments",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_id":
                invoice_data["id"],
            "amount":
                "400.00",
            "payment_method":
                "cash",
        },
    )

    payment_data = payment.json()

    reverse = await client.post(
        (
            f"{BASE_URL}/supplier-payments/"
            f"{payment_data['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Correction test",
        },
    )

    assert reverse.status_code == 200, (
        reverse.text
    )

    assert (
        reverse.json()["is_reversed"]
        is True
    )

    invoice_detail = await client.get(
        (
            f"{BASE_URL}/supplier-invoices/"
            f"{invoice_data['id']}"
        ),
        headers=admin_headers,
    )

    updated = invoice_detail.json()

    assert dec(
        updated["paid_amount"]
    ) == Decimal("0.00")

    assert dec(
        updated["balance_amount"]
    ) == Decimal("900.00")

    supplier = await db_session.get(
        Supplier,
        supplier_id,
    )

    assert dec(
        supplier.current_payable
    ) == Decimal("900.00")


@pytest.mark.asyncio
async def test_invoice_with_active_payment_cannot_be_reversed(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="985",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-985",
            "subtotal":
                "700.00",
        },
    )

    invoice_data = invoice.json()

    payment = await client.post(
        f"{BASE_URL}/supplier-payments",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_id":
                invoice_data["id"],
            "amount":
                "100.00",
            "payment_method":
                "cash",
        },
    )

    assert payment.status_code == 201

    reverse = await client.post(
        (
            f"{BASE_URL}/supplier-invoices/"
            f"{invoice_data['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Should be blocked",
        },
    )

    assert reverse.status_code == 409


@pytest.mark.asyncio
async def test_invoice_reversal_reduces_supplier_payable(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="986",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-986",
            "subtotal":
                "500.00",
        },
    )

    invoice_data = invoice.json()

    reverse = await client.post(
        (
            f"{BASE_URL}/supplier-invoices/"
            f"{invoice_data['id']}/reverse"
        ),
        headers=admin_headers,
        json={
            "reason":
                "Supplier invoice cancelled",
        },
    )

    assert reverse.status_code == 200, (
        reverse.text
    )

    assert reverse.json()["status"] == (
        "reversed"
    )

    supplier = await db_session.get(
        Supplier,
        supplier_id,
    )

    assert dec(
        supplier.current_payable
    ) == Decimal("0.00")


@pytest.mark.asyncio
async def test_overpayment_is_rejected_atomically(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="987",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    invoice = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_number":
                "SUP-INV-987",
            "subtotal":
                "300.00",
        },
    )

    invoice_data = invoice.json()

    response = await client.post(
        f"{BASE_URL}/supplier-payments",
        headers=admin_headers,
        json={
            "supplier_id":
                supplier_id,
            "supplier_invoice_id":
                invoice_data["id"],
            "amount":
                "301.00",
            "payment_method":
                "cash",
        },
    )

    assert response.status_code == 409

    result = await db_session.execute(
        select(SupplierPayment)
    )

    assert (
        result.scalars().all()
        == []
    )


@pytest.mark.asyncio
async def test_duplicate_supplier_invoice_reference_rejected(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="988",
    )

    supplier_id = (
        fixture["supplier"]["id"]
    )

    payload = {
        "supplier_id":
            supplier_id,
        "supplier_invoice_number":
            "SUP-DUP-988",
        "subtotal":
            "500.00",
    }

    first = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json=payload,
    )

    assert first.status_code == 201

    second = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json=payload,
    )

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_supplier_finance_requires_authentication(
    client,
):
    response = await client.get(
        f"{BASE_URL}/supplier-invoices"
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_supplier_invoice_allows_zero_credit_limit(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="990",
        quantity="1.000",
        unit_cost="500.00",
        discount="0.00",
        tax="0.00",
    )

    supplier = await db_session.get(
        Supplier,
        fixture["supplier"]["id"],
    )

    supplier.credit_limit = Decimal("0.00")
    await db_session.commit()

    response = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "supplier_invoice_number":
                "SUP-INV-CREDIT-ZERO",
            "subtotal":
                "500.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    await db_session.refresh(supplier)

    assert dec(
        supplier.current_payable
    ) == Decimal("500.00")


@pytest.mark.asyncio
async def test_supplier_invoice_allows_below_credit_limit(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="991",
        quantity="1.000",
        unit_cost="500.00",
        discount="0.00",
        tax="0.00",
    )

    supplier = await db_session.get(
        Supplier,
        fixture["supplier"]["id"],
    )

    supplier.credit_limit = Decimal("1000.00")
    await db_session.commit()

    response = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "supplier_invoice_number":
                "SUP-INV-CREDIT-BELOW",
            "subtotal":
                "600.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    await db_session.refresh(supplier)

    assert dec(
        supplier.current_payable
    ) == Decimal("600.00")


@pytest.mark.asyncio
async def test_supplier_invoice_allows_exact_credit_limit(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="992",
        quantity="1.000",
        unit_cost="500.00",
        discount="0.00",
        tax="0.00",
    )

    supplier = await db_session.get(
        Supplier,
        fixture["supplier"]["id"],
    )

    supplier.credit_limit = Decimal("1000.00")
    await db_session.commit()

    response = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "supplier_invoice_number":
                "SUP-INV-CREDIT-EXACT",
            "subtotal":
                "1000.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    await db_session.refresh(supplier)

    assert dec(
        supplier.current_payable
    ) == Decimal("1000.00")


@pytest.mark.asyncio
async def test_supplier_invoice_rejects_credit_limit_excess(
    client,
    admin_headers,
    db_session,
):
    fixture = await create_po_fixture(
        client,
        admin_headers,
        db_session,
        suffix="993",
        quantity="1.000",
        unit_cost="500.00",
        discount="0.00",
        tax="0.00",
    )

    supplier = await db_session.get(
        Supplier,
        fixture["supplier"]["id"],
    )

    supplier.credit_limit = Decimal("1000.00")
    await db_session.commit()

    first = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "supplier_invoice_number":
                "SUP-INV-CREDIT-FIRST",
            "subtotal":
                "800.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert first.status_code == 201, (
        first.text
    )

    second = await client.post(
        f"{BASE_URL}/supplier-invoices",
        headers=admin_headers,
        json={
            "supplier_id":
                fixture["supplier"]["id"],
            "supplier_invoice_number":
                "SUP-INV-CREDIT-OVER",
            "subtotal":
                "201.00",
            "discount_amount":
                "0.00",
            "tax_amount":
                "0.00",
        },
    )

    assert second.status_code == 409, (
        second.text
    )

    assert second.json()["detail"] == (
        "Supplier credit limit would "
        "be exceeded"
    )

    await db_session.refresh(supplier)

    assert dec(
        supplier.current_payable
    ) == Decimal("800.00")

    result = await db_session.execute(
        select(SupplierInvoice).where(
            SupplierInvoice.supplier_id
            == supplier.id,
            SupplierInvoice
            .supplier_invoice_number
            == "SUP-INV-CREDIT-OVER",
        )
    )

    assert result.scalar_one_or_none() is None


def test_supplier_invoice_aging_boundaries():
    today = date(2026, 8, 20)

    def make_invoice(
        *,
        due_date,
        balance="100.00",
        is_reversed=False,
    ):
        invoice = SupplierInvoice(
            company_id=1,
            branch_id=1,
            supplier_id=1,
            supplier_invoice_number="AGING-TEST",
            invoice_date=(
                today
            ),
            due_date=due_date,
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            grand_total=Decimal("100.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal(balance),
            status="posted",
            is_reversed=is_reversed,
            created_by_id=1,
        )

        return invoice

    cases = [
        (
            "future",
            today + timedelta(days=1),
            False,
            0,
            "Current",
        ),
        (
            "due_today",
            today,
            False,
            0,
            "Current",
        ),
        (
            "one_day",
            today - timedelta(days=1),
            True,
            1,
            "1-30 days",
        ),
        (
            "thirty_days",
            today - timedelta(days=30),
            True,
            30,
            "1-30 days",
        ),
        (
            "thirty_one_days",
            today - timedelta(days=31),
            True,
            31,
            "31-60 days",
        ),
        (
            "sixty_days",
            today - timedelta(days=60),
            True,
            60,
            "31-60 days",
        ),
        (
            "sixty_one_days",
            today - timedelta(days=61),
            True,
            61,
            "61-90 days",
        ),
        (
            "ninety_days",
            today - timedelta(days=90),
            True,
            90,
            "61-90 days",
        ),
        (
            "ninety_one_days",
            today - timedelta(days=91),
            True,
            91,
            "90+ days",
        ),
    ]

    for (
        _name,
        due_date,
        expected_overdue,
        expected_days,
        expected_bucket,
    ) in cases:
        invoice = make_invoice(
            due_date=due_date,
        )

        (
            is_overdue,
            days_overdue,
            aging_bucket,
        ) = supplier_invoice_aging(
            invoice,
            today=today,
        )

        assert is_overdue is expected_overdue
        assert days_overdue == expected_days
        assert aging_bucket == expected_bucket


def test_supplier_invoice_aging_paid_and_reversed_are_current():
    today = date(2026, 8, 20)
    overdue_due_date = (
        today - timedelta(days=45)
    )

    paid_invoice = SupplierInvoice(
        company_id=1,
        branch_id=1,
        supplier_id=1,
        supplier_invoice_number="AGING-PAID",
        invoice_date=today,
        due_date=overdue_due_date,
        subtotal=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("100.00"),
        paid_amount=Decimal("100.00"),
        balance_amount=Decimal("0.00"),
        status="paid",
        is_reversed=False,
        created_by_id=1,
    )

    assert supplier_invoice_aging(
        paid_invoice,
        today=today,
    ) == (
        False,
        0,
        "Current",
    )

    reversed_invoice = SupplierInvoice(
        company_id=1,
        branch_id=1,
        supplier_id=1,
        supplier_invoice_number="AGING-REVERSED",
        invoice_date=today,
        due_date=overdue_due_date,
        subtotal=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        grand_total=Decimal("100.00"),
        paid_amount=Decimal("0.00"),
        balance_amount=Decimal("100.00"),
        status="reversed",
        is_reversed=True,
        created_by_id=1,
    )

    assert supplier_invoice_aging(
        reversed_invoice,
        today=today,
    ) == (
        False,
        0,
        "Current",
    )
