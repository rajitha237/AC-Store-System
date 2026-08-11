import pytest


async def create_category(
    client,
    admin_headers,
    *,
    code="AIR-CON",
    name="Air Conditioners",
):
    response = await client.post(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        json={
            "code": code,
            "name": name,
            "description": "Air conditioning equipment",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


async def create_brand(
    client,
    admin_headers,
    *,
    code="DAIKIN",
    name="Daikin",
):
    response = await client.post(
        "/api/v1/catalog/brands",
        headers=admin_headers,
        json={
            "code": code,
            "name": name,
            "description": "Air conditioning brand",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


async def get_unit(client, admin_headers):
    response = await client.get(
        "/api/v1/catalog/units",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    units = response.json()
    assert units

    return units[0]


async def create_product(
    client,
    admin_headers,
    *,
    category_id,
    brand_id,
    unit_id,
    barcode="CAT-TEST-0001",
    name="12000 BTU Inverter AC",
):
    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "barcode": barcode,
            "category_id": category_id,
            "brand_id": brand_id,
            "unit_id": unit_id,
            "name": name,
            "model_number": "TEST-INV-12K",
            "description": "Integration test product",
            "btu_capacity": 12000,
            "product_type": "equipment",
            "track_serial_numbers": True,
            "purchase_cost": "100000.00",
            "selling_price": "150000.00",
            "minimum_selling_price": "140000.00",
            "warranty_months": 12,
            "reorder_level": "2.000",
            "reorder_quantity": "5.000",
            "technical_notes": "Catalog integration test",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_category_full_lifecycle(
    client,
    admin_headers,
):
    category = await create_category(
        client,
        admin_headers,
    )

    assert category["code"] == "AIR-CON"
    assert category["name"] == "Air Conditioners"
    assert category["is_active"] is True

    category_id = category["id"]

    response = await client.get(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        params={"search": "Condition"},
    )

    assert response.status_code == 200

    categories = response.json()

    assert any(
        item["id"] == category_id
        for item in categories
    )

    response = await client.patch(
        f"/api/v1/catalog/categories/{category_id}",
        headers=admin_headers,
        json={
            "name": "Residential Air Conditioners",
        },
    )

    assert response.status_code == 200, response.text
    assert (
        response.json()["name"]
        == "Residential Air Conditioners"
    )

    response = await client.delete(
        f"/api/v1/catalog/categories/{category_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_category_rejected(
    client,
    admin_headers,
):
    await create_category(
        client,
        admin_headers,
        code="DUP-CAT",
        name="Duplicate Category One",
    )

    response = await client.post(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        json={
            "code": "DUP-CAT",
            "name": "Duplicate Category Two",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_category_code_normalization(
    client,
    admin_headers,
):
    response = await client.post(
        "/api/v1/catalog/categories",
        headers=admin_headers,
        json={
            "code": "split ac",
            "name": "Split AC",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["code"] == "SPLIT-AC"


@pytest.mark.asyncio
async def test_brand_full_lifecycle(
    client,
    admin_headers,
):
    brand = await create_brand(
        client,
        admin_headers,
    )

    assert brand["code"] == "DAIKIN"
    assert brand["name"] == "Daikin"
    assert brand["is_active"] is True

    brand_id = brand["id"]

    response = await client.get(
        "/api/v1/catalog/brands",
        headers=admin_headers,
        params={"search": "Daikin"},
    )

    assert response.status_code == 200

    assert any(
        item["id"] == brand_id
        for item in response.json()
    )

    response = await client.patch(
        f"/api/v1/catalog/brands/{brand_id}",
        headers=admin_headers,
        json={
            "description": "Updated brand description",
        },
    )

    assert response.status_code == 200, response.text
    assert (
        response.json()["description"]
        == "Updated brand description"
    )

    response = await client.delete(
        f"/api/v1/catalog/brands/{brand_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_brand_rejected(
    client,
    admin_headers,
):
    await create_brand(
        client,
        admin_headers,
        code="DUP-BRAND",
        name="Duplicate Brand One",
    )

    response = await client.post(
        "/api/v1/catalog/brands",
        headers=admin_headers,
        json={
            "code": "DUP-BRAND",
            "name": "Duplicate Brand Two",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_units_are_seeded(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/catalog/units",
        headers=admin_headers,
    )

    assert response.status_code == 200

    units = response.json()

    assert len(units) >= 1

    codes = {
        item["code"]
        for item in units
    }

    assert "UNIT" in codes


@pytest.mark.asyncio
async def test_product_full_lifecycle(
    client,
    admin_headers,
):
    category = await create_category(
        client,
        admin_headers,
        code="PROD-CAT",
        name="Product Test Category",
    )

    brand = await create_brand(
        client,
        admin_headers,
        code="PROD-BRAND",
        name="Product Test Brand",
    )

    unit = await get_unit(
        client,
        admin_headers,
    )

    product = await create_product(
        client,
        admin_headers,
        category_id=category["id"],
        brand_id=brand["id"],
        unit_id=unit["id"],
    )

    assert product["product_code"].startswith("PRD-")
    assert product["name"] == "12000 BTU Inverter AC"
    assert product["product_type"] == "equipment"
    assert product["track_serial_numbers"] is True
    assert product["is_active"] is True

    product_id = product["id"]

    response = await client.get(
        f"/api/v1/catalog/products/{product_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    fetched = response.json()

    assert fetched["id"] == product_id
    assert fetched["category"]["id"] == category["id"]
    assert fetched["brand"]["id"] == brand["id"]
    assert fetched["unit"]["id"] == unit["id"]

    response = await client.get(
        "/api/v1/catalog/products",
        headers=admin_headers,
        params={
            "search": "12000",
            "product_type": "equipment",
            "track_serial_numbers": "true",
        },
    )

    assert response.status_code == 200, response.text

    listing = response.json()

    assert listing["total"] >= 1

    assert any(
        item["id"] == product_id
        for item in listing["items"]
    )

    response = await client.patch(
        f"/api/v1/catalog/products/{product_id}",
        headers=admin_headers,
        json={
            "name": "12000 BTU Premium Inverter AC",
            "selling_price": "160000.00",
            "minimum_selling_price": "145000.00",
        },
    )

    assert response.status_code == 200, response.text

    updated = response.json()

    assert (
        updated["name"]
        == "12000 BTU Premium Inverter AC"
    )
    assert updated["selling_price"] == "160000.00"

    response = await client.delete(
        f"/api/v1/catalog/products/{product_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_duplicate_product_barcode_rejected(
    client,
    admin_headers,
):
    category = await create_category(
        client,
        admin_headers,
        code="BAR-CAT",
        name="Barcode Test Category",
    )

    brand = await create_brand(
        client,
        admin_headers,
        code="BAR-BRAND",
        name="Barcode Test Brand",
    )

    unit = await get_unit(
        client,
        admin_headers,
    )

    await create_product(
        client,
        admin_headers,
        category_id=category["id"],
        brand_id=brand["id"],
        unit_id=unit["id"],
        barcode="DUPLICATE-BARCODE",
        name="First Barcode Product",
    )

    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "barcode": "DUPLICATE-BARCODE",
            "category_id": category["id"],
            "brand_id": brand["id"],
            "unit_id": unit["id"],
            "name": "Second Barcode Product",
            "product_type": "equipment",
            "selling_price": "100.00",
            "minimum_selling_price": "90.00",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_product_invalid_price_rejected(
    client,
    admin_headers,
):
    category = await create_category(
        client,
        admin_headers,
        code="PRICE-CAT",
        name="Price Test Category",
    )

    unit = await get_unit(
        client,
        admin_headers,
    )

    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "category_id": category["id"],
            "unit_id": unit["id"],
            "name": "Invalid Price Product",
            "selling_price": "100.00",
            "minimum_selling_price": "150.00",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_product_invalid_category_rejected(
    client,
    admin_headers,
):
    unit = await get_unit(
        client,
        admin_headers,
    )

    response = await client.post(
        "/api/v1/catalog/products",
        headers=admin_headers,
        json={
            "category_id": 999999,
            "unit_id": unit["id"],
            "name": "Invalid Category Product",
            "selling_price": "100.00",
            "minimum_selling_price": "90.00",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_product_not_found(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/catalog/products/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404
