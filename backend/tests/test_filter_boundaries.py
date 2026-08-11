import pytest


INVALID_ENUM_CASES = [
    (
        "/api/v1/catalog/products",
        "product_type",
        "definitely_invalid",
    ),
    (
        "/api/v1/customers",
        "customer_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/customers",
        "customer_type",
        "definitely_invalid",
    ),
    (
        "/api/v1/credit-notes",
        "credit_note_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/returns",
        "return_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/returns",
        "resolution",
        "definitely_invalid",
    ),
    (
        "/api/v1/returns",
        "return_type",
        "definitely_invalid",
    ),
    (
        "/api/v1/sales/invoices",
        "invoice_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/sales/invoices",
        "payment_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/service/jobs",
        "job_status",
        "definitely_invalid",
    ),
    (
        "/api/v1/service/jobs",
        "priority",
        "definitely_invalid",
    ),
    (
        "/api/v1/service/jobs",
        "service_type",
        "definitely_invalid",
    ),
    (
        "/api/v1/inventory/movements",
        "movement_type",
        "definitely_invalid",
    ),
]


BOOLEAN_CASES = [
    (
        "/api/v1/catalog/products",
        "is_active",
    ),
    (
        "/api/v1/catalog/products",
        "track_serial_numbers",
    ),
    (
        "/api/v1/payments",
        "is_reversed",
    ),
    (
        "/api/v1/service/jobs",
        "warranty_only",
    ),
    (
        "/api/v1/suppliers",
        "is_active",
    ),
]


POSITIVE_ID_CASES = [
    (
        "/api/v1/audit-logs",
        "user_id",
    ),
    (
        "/api/v1/audit-logs",
        "entity_id",
    ),
    (
        "/api/v1/catalog/products",
        "brand_id",
    ),
    (
        "/api/v1/catalog/products",
        "category_id",
    ),
    (
        "/api/v1/inventory/movements",
        "product_id",
    ),
    (
        "/api/v1/inventory/movements",
        "serial_number_id",
    ),
    (
        "/api/v1/inventory/movements",
        "warehouse_id",
    ),
    (
        "/api/v1/payments",
        "customer_id",
    ),
    (
        "/api/v1/payments",
        "invoice_id",
    ),
    (
        "/api/v1/service/jobs",
        "customer_id",
    ),
    (
        "/api/v1/service/jobs",
        "technician_id",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "path",
        "parameter",
        "value",
    ),
    INVALID_ENUM_CASES,
)
async def test_invalid_enum_filters_rejected(
    client,
    admin_headers,
    path,
    parameter,
    value,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            parameter:
                value,
        },
    )

    assert response.status_code == 422, (
        path,
        parameter,
        response.status_code,
        response.text,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "path",
        "parameter",
    ),
    BOOLEAN_CASES,
)
@pytest.mark.parametrize(
    "value",
    [
        "definitely_invalid",
        "2",
        "maybe",
    ],
)
async def test_invalid_boolean_filters_rejected(
    client,
    admin_headers,
    path,
    parameter,
    value,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            parameter:
                value,
        },
    )

    assert response.status_code == 422, (
        path,
        parameter,
        value,
        response.status_code,
        response.text,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "path",
        "parameter",
    ),
    POSITIVE_ID_CASES,
)
@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
        "abc",
    ],
)
async def test_invalid_filter_ids_rejected(
    client,
    admin_headers,
    path,
    parameter,
    value,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            parameter:
                value,
        },
    )

    assert response.status_code == 422, (
        path,
        parameter,
        value,
        response.status_code,
        response.text,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/audit-logs",
    ],
)
@pytest.mark.parametrize(
    (
        "parameter",
        "value",
    ),
    [
        (
            "date_from",
            "not-a-date",
        ),
        (
            "date_to",
            "not-a-date",
        ),
        (
            "date_from",
            "2026-99-99",
        ),
        (
            "date_to",
            "2026-99-99",
        ),
    ],
)
async def test_invalid_date_filters_rejected(
    client,
    admin_headers,
    path,
    parameter,
    value,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            parameter:
                value,
        },
    )

    assert response.status_code == 422, (
        response.status_code,
        response.text,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/customers",
        "/api/v1/suppliers",
        "/api/v1/catalog/products",
        "/api/v1/sales/invoices",
        "/api/v1/payments",
        "/api/v1/returns",
        "/api/v1/credit-notes",
        "/api/v1/service/jobs",
        "/api/v1/audit-logs",
    ],
)
async def test_non_matching_search_returns_safe_empty_result(
    client,
    admin_headers,
    path,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            "search":
                "ZZZ-NO-MATCH-"
                "1234567890-"
                "UNIQUE-BOUNDARY",
            "page":
                1,
            "page_size":
                20,
        },
    )

    assert response.status_code == 200, (
        path,
        response.text,
    )

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 0


@pytest.mark.asyncio
async def test_valid_boolean_spellings_accepted(
    client,
    admin_headers,
):
    for value in (
        "true",
        "false",
        "1",
        "0",
    ):
        response = await client.get(
            "/api/v1/suppliers",
            headers=admin_headers,
            params={
                "is_active":
                    value,
            },
        )

        assert response.status_code == 200, (
            value,
            response.text,
        )


@pytest.mark.asyncio
async def test_combined_customer_filters_are_safe(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/customers",
        headers=admin_headers,
        params={
            "page":
                1,
            "page_size":
                5,
            "search":
                "NO-MATCH-COMBINED",
            "customer_status":
                "active",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_combined_service_filters_are_safe(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/service/jobs",
        headers=admin_headers,
        params={
            "page":
                1,
            "page_size":
                5,
            "search":
                "NO-MATCH-COMBINED",
            "warranty_only":
                "true",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 5
