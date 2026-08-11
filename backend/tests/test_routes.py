import pytest

from app.main import app


@pytest.mark.asyncio
async def test_required_openapi_routes_exist():
    schema = app.openapi()

    paths = set(
        schema.get(
            "paths",
            {},
        )
    )

    required = {
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/customers",
        "/api/v1/inventory/balances",
        "/api/v1/sales/invoices",
        "/api/v1/payments",
        "/api/v1/returns",
        "/api/v1/credit-notes",
        "/api/v1/service/jobs",
        "/api/v1/audit-logs",
    }

    missing = (
        required - paths
    )

    assert not missing
