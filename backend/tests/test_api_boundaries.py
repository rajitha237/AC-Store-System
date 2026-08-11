import pytest

from app.main import app


PAGINATED_GET_ROUTES = [
    "/api/v1/audit-logs",
    "/api/v1/catalog/products",
    "/api/v1/credit-notes",
    "/api/v1/customers",
    "/api/v1/inventory/movements",
    "/api/v1/payments",
    "/api/v1/returns",
    "/api/v1/sales/invoices",
    "/api/v1/service/jobs",
    "/api/v1/suppliers",
]


def get_query_parameter(
    path: str,
    parameter_name: str,
) -> dict:
    schema = app.openapi()

    operation = schema["paths"][path]["get"]

    for parameter in operation.get(
        "parameters",
        [],
    ):
        if (
            parameter.get("in") == "query"
            and parameter.get("name")
            == parameter_name
        ):
            return parameter

    raise AssertionError(
        f"{parameter_name!r} query parameter "
        f"was not found on {path}"
    )


@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
def test_pagination_openapi_contract(
    path,
):
    page = get_query_parameter(
        path,
        "page",
    )["schema"]

    page_size = get_query_parameter(
        path,
        "page_size",
    )["schema"]

    assert page["minimum"] == 1
    assert page["default"] == 1

    assert page_size["minimum"] == 1
    assert page_size["maximum"] == 100
    assert page_size["default"] == 20


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
@pytest.mark.parametrize(
    "params",
    [
        {
            "page": 0,
        },
        {
            "page": -1,
        },
        {
            "page_size": 0,
        },
        {
            "page_size": -1,
        },
        {
            "page_size": 101,
        },
    ],
)
async def test_invalid_pagination_boundaries_rejected(
    client,
    admin_headers,
    path,
    params,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params=params,
    )

    assert response.status_code == 422, (
        path,
        params,
        response.text,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
async def test_maximum_page_size_accepted(
    client,
    admin_headers,
    path,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            "page": 1,
            "page_size": 100,
        },
    )

    assert response.status_code == 200, (
        path,
        response.text,
    )

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 100

    assert isinstance(
        data["items"],
        list,
    )

    assert isinstance(
        data["total"],
        int,
    )

    assert isinstance(
        data["total_pages"],
        int,
    )

    assert len(data["items"]) <= 100


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
async def test_far_away_page_is_safe_and_empty(
    client,
    admin_headers,
    path,
):
    response = await client.get(
        path,
        headers=admin_headers,
        params={
            "page": 999999,
            "page_size": 20,
        },
    )

    assert response.status_code == 200, (
        path,
        response.text,
    )

    data = response.json()

    assert data["page"] == 999999
    assert data["page_size"] == 20
    assert data["items"] == []

    assert data["total"] >= 0
    assert data["total_pages"] >= 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
async def test_default_pagination_metadata(
    client,
    admin_headers,
    path,
):
    response = await client.get(
        path,
        headers=admin_headers,
    )

    assert response.status_code == 200, (
        path,
        response.text,
    )

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 20

    assert isinstance(
        data["items"],
        list,
    )

    assert isinstance(
        data["total"],
        int,
    )

    assert isinstance(
        data["total_pages"],
        int,
    )

    assert data["total"] >= 0
    assert data["total_pages"] >= 0

    assert len(data["items"]) <= 20


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    PAGINATED_GET_ROUTES,
)
async def test_pagination_rejects_non_integer_values(
    client,
    admin_headers,
    path,
):
    for params in (
        {
            "page": "abc",
        },
        {
            "page": "1.5",
        },
        {
            "page_size": "abc",
        },
        {
            "page_size": "1.5",
        },
    ):
        response = await client.get(
            path,
            headers=admin_headers,
            params=params,
        )

        assert response.status_code == 422, (
            path,
            params,
            response.text,
        )
