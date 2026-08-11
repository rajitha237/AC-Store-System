import pytest


BASE_URL = "/api/v1/suppliers"


def supplier_payload(
    *,
    company_name: str = "Cool Air Lanka",
    phone: str = "0771234567",
    email: str | None = "sales@coolair.lk",
) -> dict:
    return {
        "company_name": company_name,
        "contact_person": "Nimal Perera",
        "phone": phone,
        "secondary_phone": "0712345678",
        "email": email,
        "address_line_1": "100 Main Street",
        "address_line_2": "Colombo 03",
        "city": "Colombo",
        "registration_number": "PV-TEST-001",
        "tax_number": "TIN-TEST-001",
        "credit_limit": "250000.00",
        "payment_terms_days": 30,
        "notes": "Supplier integration test",
    }


async def create_supplier(
    client,
    admin_headers,
    **overrides,
):
    payload = supplier_payload(**overrides)

    response = await client.post(
        BASE_URL,
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text

    return response.json()


@pytest.mark.asyncio
async def test_supplier_full_lifecycle(
    client,
    admin_headers,
):
    create_response = await client.post(
        BASE_URL,
        json=supplier_payload(),
        headers=admin_headers,
    )

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["id"] > 0
    assert created["supplier_code"].startswith("SUP-")
    assert created["company_name"] == "Cool Air Lanka"
    assert created["phone"] == "0771234567"
    assert created["email"] == "sales@coolair.lk"
    assert created["credit_limit"] == "250000.00"
    assert created["payment_terms_days"] == 30
    assert created["current_payable"] == "0.00"
    assert created["is_active"] is True
    assert created["created_by_id"] > 0

    supplier_id = created["id"]

    get_response = await client.get(
        f"{BASE_URL}/{supplier_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200

    fetched = get_response.json()

    assert fetched["id"] == supplier_id
    assert fetched["supplier_code"] == created["supplier_code"]

    patch_response = await client.patch(
        f"{BASE_URL}/{supplier_id}",
        json={
            "company_name": "Cool Air Lanka Updated",
            "contact_person": "Kamal Perera",
            "city": "Kandy",
            "credit_limit": "300000.00",
            "payment_terms_days": 45,
            "notes": "Updated supplier",
        },
        headers=admin_headers,
    )

    assert patch_response.status_code == 200

    updated = patch_response.json()

    assert updated["company_name"] == (
        "Cool Air Lanka Updated"
    )
    assert updated["contact_person"] == "Kamal Perera"
    assert updated["city"] == "Kandy"
    assert updated["credit_limit"] == "300000.00"
    assert updated["payment_terms_days"] == 45
    assert updated["notes"] == "Updated supplier"
    assert updated["updated_by_id"] > 0

    delete_response = await client.delete(
        f"{BASE_URL}/{supplier_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200

    deactivated = delete_response.json()

    assert deactivated["id"] == supplier_id
    assert deactivated["is_active"] is False

    final_response = await client.get(
        f"{BASE_URL}/{supplier_id}",
        headers=admin_headers,
    )

    assert final_response.status_code == 200
    assert final_response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_supplier_defaults(
    client,
    admin_headers,
):
    response = await client.post(
        BASE_URL,
        json={
            "company_name": "Default Supplier",
            "phone": "0772000001",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["credit_limit"] == "0.00"
    assert data["payment_terms_days"] == 0
    assert data["current_payable"] == "0.00"
    assert data["is_active"] is True
    assert data["email"] is None


@pytest.mark.asyncio
async def test_supplier_normalization(
    client,
    admin_headers,
):
    response = await client.post(
        BASE_URL,
        json={
            "company_name": "  Normalized Supplier  ",
            "phone": "0773000001",
            "email": "  SALES@EXAMPLE.COM  ",
            "city": "  Colombo  ",
        },
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["company_name"] == "Normalized Supplier"
    assert data["email"] == "sales@example.com"
    assert data["city"] == "Colombo"


@pytest.mark.asyncio
async def test_duplicate_supplier_company_name_rejected(
    client,
    admin_headers,
):
    await create_supplier(
        client,
        admin_headers,
        company_name="Duplicate Company",
        phone="0774000001",
        email="first@example.com",
    )

    response = await client.post(
        BASE_URL,
        json=supplier_payload(
            company_name="duplicate company",
            phone="0774000002",
            email="second@example.com",
        ),
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A supplier with this company name already exists"
    )


@pytest.mark.asyncio
async def test_duplicate_supplier_phone_rejected(
    client,
    admin_headers,
):
    await create_supplier(
        client,
        admin_headers,
        company_name="Phone Supplier One",
        phone="0775000001",
        email="phone1@example.com",
    )

    response = await client.post(
        BASE_URL,
        json=supplier_payload(
            company_name="Phone Supplier Two",
            phone="0775000001",
            email="phone2@example.com",
        ),
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A supplier with this phone number already exists"
    )


@pytest.mark.asyncio
async def test_duplicate_supplier_email_rejected(
    client,
    admin_headers,
):
    await create_supplier(
        client,
        admin_headers,
        company_name="Email Supplier One",
        phone="0776000001",
        email="duplicate@example.com",
    )

    response = await client.post(
        BASE_URL,
        json=supplier_payload(
            company_name="Email Supplier Two",
            phone="0776000002",
            email="DUPLICATE@EXAMPLE.COM",
        ),
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A supplier with this email address already exists"
    )


@pytest.mark.asyncio
async def test_supplier_invalid_email_rejected(
    client,
    admin_headers,
):
    response = await client.post(
        BASE_URL,
        json=supplier_payload(
            company_name="Invalid Email Supplier",
            phone="0777000001",
            email="invalid-email",
        ),
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_supplier_invalid_credit_limit_rejected(
    client,
    admin_headers,
):
    payload = supplier_payload(
        company_name="Invalid Credit Supplier",
        phone="0777000002",
        email="credit@example.com",
    )

    payload["credit_limit"] = "-1.00"

    response = await client.post(
        BASE_URL,
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_supplier_invalid_payment_terms_rejected(
    client,
    admin_headers,
):
    payload = supplier_payload(
        company_name="Invalid Terms Supplier",
        phone="0777000003",
        email="terms@example.com",
    )

    payload["payment_terms_days"] = 366

    response = await client.post(
        BASE_URL,
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_supplier_search_and_active_filter(
    client,
    admin_headers,
):
    first = await create_supplier(
        client,
        admin_headers,
        company_name="Arctic Cooling Systems",
        phone="0778000001",
        email="arctic@example.com",
    )

    await create_supplier(
        client,
        admin_headers,
        company_name="Tropical Engineering",
        phone="0778000002",
        email="tropical@example.com",
    )

    search_response = await client.get(
        BASE_URL,
        params={
            "search": "Arctic",
        },
        headers=admin_headers,
    )

    assert search_response.status_code == 200

    search_data = search_response.json()

    assert search_data["total"] == 1
    assert len(search_data["items"]) == 1
    assert (
        search_data["items"][0]["id"]
        == first["id"]
    )

    delete_response = await client.delete(
        f"{BASE_URL}/{first['id']}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200

    inactive_response = await client.get(
        BASE_URL,
        params={
            "is_active": "false",
        },
        headers=admin_headers,
    )

    assert inactive_response.status_code == 200

    inactive_data = inactive_response.json()

    inactive_ids = {
        item["id"]
        for item in inactive_data["items"]
    }

    assert first["id"] in inactive_ids

    active_response = await client.get(
        BASE_URL,
        params={
            "is_active": "true",
        },
        headers=admin_headers,
    )

    assert active_response.status_code == 200

    active_ids = {
        item["id"]
        for item in active_response.json()["items"]
    }

    assert first["id"] not in active_ids


@pytest.mark.asyncio
async def test_supplier_pagination(
    client,
    admin_headers,
):
    for index in range(5):
        await create_supplier(
            client,
            admin_headers,
            company_name=f"Page Supplier {index:02d}",
            phone=f"07790000{index:02d}",
            email=f"page{index}@example.com",
        )

    response = await client.get(
        BASE_URL,
        params={
            "page": 2,
            "page_size": 2,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 5
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total_pages"] == 3
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_supplier_update_duplicate_rejected(
    client,
    admin_headers,
):
    first = await create_supplier(
        client,
        admin_headers,
        company_name="Update Supplier One",
        phone="0761000001",
        email="update1@example.com",
    )

    second = await create_supplier(
        client,
        admin_headers,
        company_name="Update Supplier Two",
        phone="0761000002",
        email="update2@example.com",
    )

    response = await client.patch(
        f"{BASE_URL}/{second['id']}",
        json={
            "company_name": first["company_name"],
        },
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "A supplier with this company name already exists"
    )


@pytest.mark.asyncio
async def test_supplier_not_found(
    client,
    admin_headers,
):
    response = await client.get(
        f"{BASE_URL}/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Supplier record was not found"
    )
