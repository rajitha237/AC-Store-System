import pytest


def customer_payload(
    *,
    full_name="Customer Integration Test",
    nic_number="991234567V",
    primary_phone="0771234567",
    email="customer.integration@example.com",
):
    return {
        "customer_type": "cash",
        "full_name": full_name,
        "business_name": "Integration Test Business",
        "nic_number": nic_number,
        "registration_number": "REG-TEST-001",
        "primary_phone": primary_phone,
        "secondary_phone": "0711234567",
        "sms_phone": primary_phone,
        "email": email,
        "address_line_1": "100 Test Road",
        "address_line_2": "Test Building",
        "city": "Colombo",
        "district": "Colombo",
        "province": "Western",
        "postal_code": "00100",
        "credit_status": "restricted",
        "credit_limit": "0.00",
        "sms_allowed": True,
        "notes": "Customer integration pytest fixture",
    }


@pytest.mark.asyncio
async def test_customer_full_lifecycle(
    client,
    admin_headers,
):
    #
    # CREATE
    #
    create_response = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(),
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    created = create_response.json()

    customer_id = created["id"]

    assert customer_id >= 1

    assert (
        created["customer_number"]
        == f"CUS-{customer_id:06d}"
    )

    assert (
        created["full_name"]
        == "Customer Integration Test"
    )

    assert (
        created["primary_phone"]
        == "0771234567"
    )

    assert created["customer_type"] == "cash"
    assert created["status"] == "active"
    assert created["credit_status"] == "restricted"

    #
    # GET
    #
    get_response = await client.get(
        f"/api/v1/customers/{customer_id}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200

    fetched = get_response.json()

    assert fetched["id"] == customer_id
    assert (
        fetched["customer_number"]
        == created["customer_number"]
    )

    #
    # LIST
    #
    list_response = await client.get(
        "/api/v1/customers",
        headers=admin_headers,
    )

    assert list_response.status_code == 200

    listed = list_response.json()

    assert listed["total"] >= 1
    assert listed["page"] == 1
    assert listed["page_size"] >= 1

    assert any(
        item["id"] == customer_id
        for item in listed["items"]
    )

    #
    # SEARCH BY NAME
    #
    search_response = await client.get(
        "/api/v1/customers",
        headers=admin_headers,
        params={
            "search":
                "Customer Integration Test",
        },
    )

    assert search_response.status_code == 200

    search_data = search_response.json()

    assert any(
        item["id"] == customer_id
        for item in search_data["items"]
    )

    #
    # SEARCH BY PHONE
    #
    phone_search_response = await client.get(
        "/api/v1/customers",
        headers=admin_headers,
        params={
            "search":
                "0771234567",
        },
    )

    assert phone_search_response.status_code == 200

    phone_search_data = (
        phone_search_response.json()
    )

    assert any(
        item["id"] == customer_id
        for item in phone_search_data["items"]
    )

    #
    # FILTER BY TYPE
    #
    type_response = await client.get(
        "/api/v1/customers",
        headers=admin_headers,
        params={
            "customer_type":
                "cash",
        },
    )

    assert type_response.status_code == 200

    type_data = type_response.json()

    assert any(
        item["id"] == customer_id
        for item in type_data["items"]
    )

    #
    # PATCH
    #
    patch_response = await client.patch(
        f"/api/v1/customers/{customer_id}",
        headers=admin_headers,
        json={
            "full_name":
                "Customer Integration Updated",
            "customer_type":
                "credit",
            "credit_status":
                "allowed",
            "credit_limit":
                "50000.00",
            "city":
                "Kandy",
            "notes":
                "Updated by customer integration test",
        },
    )

    assert patch_response.status_code == 200, (
        patch_response.text
    )

    updated = patch_response.json()

    assert (
        updated["full_name"]
        == "Customer Integration Updated"
    )

    assert updated["customer_type"] == "credit"
    assert updated["credit_status"] == "allowed"

    assert (
        str(updated["credit_limit"])
        in {
            "50000.0",
            "50000.00",
        }
    )

    assert updated["city"] == "Kandy"

    #
    # DELETE = DEACTIVATE
    #
    delete_response = await client.delete(
        f"/api/v1/customers/{customer_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200, (
        delete_response.text
    )

    deactivated = delete_response.json()

    assert deactivated["id"] == customer_id
    assert deactivated["status"] == "inactive"

    #
    # RECORD MUST STILL EXIST
    #
    final_get_response = await client.get(
        f"/api/v1/customers/{customer_id}",
        headers=admin_headers,
    )

    assert final_get_response.status_code == 200

    final_customer = final_get_response.json()

    assert final_customer["id"] == customer_id
    assert final_customer["status"] == "inactive"


@pytest.mark.asyncio
async def test_customer_duplicate_nic_rejected(
    client,
    admin_headers,
):
    first = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="NIC Customer One",
            nic_number="881234567V",
            primary_phone="0772000001",
            email="nic.one@example.com",
        ),
    )

    assert first.status_code == 201, first.text

    duplicate = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="NIC Customer Two",
            nic_number="881234567V",
            primary_phone="0772000002",
            email="nic.two@example.com",
        ),
    )

    assert duplicate.status_code == 409

    assert (
        duplicate.json()["detail"]
        == "A customer with this NIC number already exists"
    )


@pytest.mark.asyncio
async def test_customer_duplicate_phone_rejected(
    client,
    admin_headers,
):
    first = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="Phone Customer One",
            nic_number="771234561V",
            primary_phone="0773000001",
            email="phone.one@example.com",
        ),
    )

    assert first.status_code == 201, first.text

    duplicate = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="Phone Customer Two",
            nic_number="771234562V",
            primary_phone="0773000001",
            email="phone.two@example.com",
        ),
    )

    assert duplicate.status_code == 409

    assert (
        duplicate.json()["detail"]
        == (
            "A customer with this primary phone "
            "number already exists"
        )
    )


@pytest.mark.asyncio
async def test_customer_duplicate_email_rejected(
    client,
    admin_headers,
):
    first = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="Email Customer One",
            nic_number="661234561V",
            primary_phone="0774000001",
            email="duplicate.customer@example.com",
        ),
    )

    assert first.status_code == 201, first.text

    duplicate = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=customer_payload(
            full_name="Email Customer Two",
            nic_number="661234562V",
            primary_phone="0774000002",
            email="duplicate.customer@example.com",
        ),
    )

    assert duplicate.status_code == 409

    assert (
        duplicate.json()["detail"]
        == (
            "A customer with this email address "
            "already exists"
        )
    )


@pytest.mark.asyncio
async def test_customer_invalid_email_rejected(
    client,
    admin_headers,
):
    payload = customer_payload(
        full_name="Invalid Email Customer",
        nic_number="551234567V",
        primary_phone="0775000001",
        email="not-an-email",
    )

    response = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_customer_not_found(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/customers/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Customer record was not found"
    )
