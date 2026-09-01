from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.api.v1.installments import router
from app.models.installment import InstallmentPlan
from app.schemas.installment import (
    InstallmentPaymentResponse,
    LegacyInstallmentPlanCreate,
)
from app.services.installment import (
    create_legacy_installment_plan,
    receive_installment_payment,
    reverse_installment_payment,
)


def test_legacy_create_payload_contract() -> None:
    payload = LegacyInstallmentPlanCreate(
        customer_id=1,
        principal_amount=Decimal("120000.00"),
        first_due_date=date(2026, 10, 1),
        balance_mode="register_new_debt",
        notes="Old customer balance",
    )

    assert payload.customer_id == 1
    assert payload.principal_amount == Decimal(
        "120000.00"
    )


def test_installment_model_supports_optional_invoice() -> None:
    column = InstallmentPlan.__table__.c.invoice_id

    assert column.nullable is True


def test_installment_model_has_legacy_source_fields() -> None:
    columns = InstallmentPlan.__table__.c

    assert "source_type" in columns
    assert "legacy_principal_amount" in columns


def test_legacy_create_is_fixed_to_six_installments() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert "installment_count = 6" in source


def test_legacy_create_is_monthly() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert (
        "InstallmentFrequency.MONTHLY.value"
        in source
    )


def test_legacy_create_has_zero_interest() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert (
        'interest_rate = Decimal("0.0000")'
        in source
    )

    assert "interest_amount = ZERO" in source


def test_legacy_create_does_not_create_fake_invoice() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert "invoice_id=None" in source
    assert 'source_type="legacy_debt"' in source


def test_legacy_create_supports_safe_balance_modes() -> None:
    fields = LegacyInstallmentPlanCreate.model_fields

    assert "balance_mode" in fields

    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert (
        'payload.balance_mode == "register_new_debt"'
        in source
    )
    assert (
        'payload.balance_mode == "use_existing_balance"'
        in source
    )


def test_existing_balance_is_not_added_twice() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    mutation = (
        "customer.current_balance = money("
    )

    assert source.count(mutation) == 1
    assert (
        'if payload.balance_mode == "register_new_debt":'
        in source
    )


def test_existing_balance_must_match_principal() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert "principal_amount != existing_balance" in source


def test_legacy_create_blocks_existing_active_plan() -> None:
    source = inspect.getsource(
        create_legacy_installment_plan
    )

    assert "existing_plan_id is not None" in source
    assert "already has an active " in source
    assert "installment agreement" in source


def test_legacy_payment_uses_plan_company_and_branch() -> None:
    source = inspect.getsource(
        receive_installment_payment
    )

    assert "company_id=plan.company_id" in source
    assert "branch_id=plan.branch_id" in source


def test_legacy_payment_supports_no_invoice() -> None:
    source = inspect.getsource(
        receive_installment_payment
    )

    assert "get_optional_plan_invoice" in source
    assert "if invoice is not None" in source


def test_legacy_reversal_supports_no_invoice() -> None:
    source = inspect.getsource(
        reverse_installment_payment
    )

    assert "get_optional_plan_invoice" in source

    assert (
        "if payment.invoice_id != plan.invoice_id:"
        in source
    )


def test_payment_response_invoice_fields_are_optional() -> None:
    fields = InstallmentPaymentResponse.model_fields

    invoice_id_annotation = str(
        fields["invoice_id"].annotation
    )

    invoice_number_annotation = str(
        fields["invoice_number"].annotation
    )

    assert "None" in invoice_id_annotation
    assert "None" in invoice_number_annotation


def test_legacy_api_route_exists() -> None:
    paths = {
        route.path
        for route in router.routes
    }

    assert "/installments/legacy" in paths


def test_normal_installment_create_route_is_preserved() -> None:
    paths = {
        (
            route.path,
            tuple(
                sorted(
                    route.methods or []
                )
            ),
        )
        for route in router.routes
    }

    assert (
        "/installments",
        ("POST",),
    ) in paths


def test_legacy_migration_contract() -> None:
    migration = Path(
        "alembic/versions/"
        "877748e87094_"
        "support_legacy_debt_"
        "installment_plans.py"
    )

    text = migration.read_text()

    assert (
        "down_revision"
        in text
        and "75e5e5130acb"
        in text
    )

    assert (
        "'source_type'"
        in text
    )

    assert (
        "'legacy_principal_amount'"
        in text
    )

    assert (
        "'invoice_id'"
        in text
        and "nullable=True"
        in text
    )
