from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import StockItem
from app.models.service import ServiceJobCard
from tests.test_inventory import (
    create_product,
    get_warehouse,
    receive_non_serialized,
)


BASE_URL = "/api/v1/service/jobs"


def dec(value) -> Decimal:
    return Decimal(str(value))


async def create_customer(
    client,
    admin_headers,
    *,
    suffix,
):
    response = await client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "customer_type":
                "credit",
            "full_name":
                f"Service Customer {suffix}",
            "business_name":
                f"Service Business {suffix}",
            "nic_number":
                f"200200000{int(suffix):03d}",
            "primary_phone":
                f"0758{int(suffix):06d}",
            "sms_phone":
                f"0758{int(suffix):06d}",
            "email":
                f"service{suffix}@example.com",
            "address_line_1":
                "Service Integration Address",
            "city":
                "Colombo",
            "credit_status":
                "allowed",
            "credit_limit":
                "500000.00",
            "sms_allowed":
                True,
            "notes":
                "Service integration customer",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


async def create_job(
    client,
    admin_headers,
    *,
    customer_id,
    suffix,
    product_id=None,
    is_warranty_job=False,
):
    payload = {
        "customer_id":
            customer_id,
        "complaint":
            f"Cooling issue {suffix}",
        "reported_issue":
            f"Reported service issue {suffix}",
        "service_type":
            (
                "warranty"
                if is_warranty_job
                else "repair"
            ),
        "priority":
            "normal",
        "is_warranty_job":
            is_warranty_job,
        "accessories_received":
            "Remote controller",
        "physical_condition":
            "Good",
        "special_notes":
            "Service pytest job",
        "estimated_cost":
            "0.00",
    }

    if product_id is not None:
        payload["product_id"] = product_id

    response = await client.post(
        BASE_URL,
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 201, (
        "SERVICE JOB CREATE FAILED: "
        f"{response.status_code} "
        f"{response.text}"
    )

    return response.json()


async def change_status(
    client,
    admin_headers,
    job_id,
    new_status,
    *,
    remarks=None,
):
    payload = {
        "new_status":
            new_status,
    }

    if remarks is not None:
        payload["remarks"] = remarks

    return await client.post(
        f"{BASE_URL}/{job_id}/status",
        headers=admin_headers,
        json=payload,
    )


async def move_to_inspection(
    client,
    admin_headers,
    job_id,
):
    response = await change_status(
        client,
        admin_headers,
        job_id,
        "inspection",
        remarks="Inspection started",
    )

    assert response.status_code == 200, (
        response.text
    )

    return response.json()


async def move_to_approved(
    client,
    admin_headers,
    job_id,
):
    await move_to_inspection(
        client,
        admin_headers,
        job_id,
    )

    waiting = await change_status(
        client,
        admin_headers,
        job_id,
        "waiting_approval",
        remarks="Estimate sent to customer",
    )

    assert waiting.status_code == 200, (
        waiting.text
    )

    assert (
        waiting.json()["approval_status"]
        == "pending"
    )

    approval = await client.post(
        f"{BASE_URL}/{job_id}/approval",
        headers=admin_headers,
        json={
            "approval_status":
                "approved",
            "remarks":
                "Customer approved estimate",
        },
    )

    assert approval.status_code == 200, (
        approval.text
    )

    data = approval.json()

    assert data["status"] == "approved"
    assert (
        data["approval_status"]
        == "approved"
    )

    return data


async def move_to_testing(
    client,
    admin_headers,
    job_id,
):
    await move_to_approved(
        client,
        admin_headers,
        job_id,
    )

    repairing = await change_status(
        client,
        admin_headers,
        job_id,
        "repairing",
        remarks="Repair started",
    )

    assert repairing.status_code == 200, (
        repairing.text
    )

    testing = await change_status(
        client,
        admin_headers,
        job_id,
        "testing",
        remarks="Repair completed; testing",
    )

    assert testing.status_code == 200, (
        testing.text
    )

    return testing.json()


async def move_to_ready(
    client,
    admin_headers,
    job_id,
):
    await move_to_testing(
        client,
        admin_headers,
        job_id,
    )

    update = await client.patch(
        f"{BASE_URL}/{job_id}",
        headers=admin_headers,
        json={
            "testing_result":
                "All functional tests passed",
            "work_performed":
                "Repair work completed",
        },
    )

    assert update.status_code == 200, (
        update.text
    )

    ready = await change_status(
        client,
        admin_headers,
        job_id,
        "ready",
        remarks="Ready for customer collection",
    )

    assert ready.status_code == 200, (
        ready.text
    )

    data = ready.json()

    assert data["status"] == "ready"
    assert data["completed_at"] is not None

    return data


@pytest.mark.asyncio
async def test_service_job_create_list_get_update(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="301",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="301",
    )

    assert job["job_number"].startswith(
        "JOB-"
    )
    assert job["customer_id"] == customer["id"]
    assert job["status"] == "received"
    assert (
        job["approval_status"]
        == "not_required"
    )
    assert job["service_type"] == "repair"
    assert job["priority"] == "normal"
    assert len(job["status_history"]) == 1
    assert (
        job["status_history"][0]["new_status"]
        == "received"
    )

    get_response = await client.get(
        f"{BASE_URL}/{job['id']}",
        headers=admin_headers,
    )

    assert get_response.status_code == 200
    assert (
        get_response.json()["id"]
        == job["id"]
    )

    list_response = await client.get(
        BASE_URL,
        headers=admin_headers,
        params={
            "search":
                job["job_number"],
            "job_status":
                "received",
            "customer_id":
                customer["id"],
        },
    )

    assert list_response.status_code == 200

    listing = list_response.json()

    assert listing["total"] == 1
    assert (
        listing["items"][0]["id"]
        == job["id"]
    )

    patch_response = await client.patch(
        f"{BASE_URL}/{job['id']}",
        headers=admin_headers,
        json={
            "technician_diagnosis":
                "Compressor capacitor weak",
            "special_notes":
                "Updated from integration test",
            "estimated_cost":
                "2500.00",
        },
    )

    assert patch_response.status_code == 200

    updated = patch_response.json()

    assert (
        updated["technician_diagnosis"]
        == "Compressor capacitor weak"
    )
    assert dec(
        updated["estimated_cost"]
    ) == Decimal("2500.00")


@pytest.mark.asyncio
async def test_invalid_service_status_transition_rejected(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="302",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="302",
    )

    response = await change_status(
        client,
        admin_headers,
        job["id"],
        "ready",
    )

    assert response.status_code == 409

    assert (
        "Invalid service status transition"
        in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_service_approval_flow(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="303",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="303",
    )

    approved = await move_to_approved(
        client,
        admin_headers,
        job["id"],
    )

    assert approved["status"] == "approved"
    assert approved["approval_at"] is not None

    history_statuses = [
        item["new_status"]
        for item in approved["status_history"]
    ]

    assert "received" in history_statuses
    assert "inspection" in history_statuses
    assert "waiting_approval" in history_statuses
    assert "approved" in history_statuses


@pytest.mark.asyncio
async def test_labour_state_guard_and_totals(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="304",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="304",
    )

    blocked = await client.post(
        f"{BASE_URL}/{job['id']}/labour",
        headers=admin_headers,
        json={
            "description":
                "Initial inspection",
            "hours":
                "1.00",
            "amount":
                "1500.00",
        },
    )

    assert blocked.status_code == 409
    assert (
        "Labour can only be added"
        in blocked.json()["detail"]
    )

    await move_to_inspection(
        client,
        admin_headers,
        job["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{job['id']}/labour",
        headers=admin_headers,
        json={
            "description":
                "Diagnostic labour",
            "hours":
                "1.50",
            "amount":
                "2250.00",
            "notes":
                "Service labour test",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    data = response.json()

    assert len(data["labour_items"]) == 1
    assert dec(
        data["labour_total"]
    ) == Decimal("2250.00")
    assert dec(
        data["final_amount"]
    ) == Decimal("2250.00")


@pytest.mark.asyncio
async def test_service_part_deducts_stock_and_updates_totals(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="305",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="305",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="10.000",
        unit_cost="100.00",
        reference_id="SERVICE-OPEN-305",
    )

    assert received.status_code == 201

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="305",
        product_id=product["id"],
    )

    await move_to_approved(
        client,
        admin_headers,
        job["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{job['id']}/parts",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "quantity":
                "2.000",
            "unit_price":
                "175.00",
            "notes":
                "Replacement service part",
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    data = response.json()

    assert len(data["parts"]) == 1
    assert dec(
        data["parts_total"]
    ) == Decimal("350.00")
    assert dec(
        data["final_amount"]
    ) == Decimal("350.00")

    stock = (
        await db_session.execute(
            select(StockItem)
            .where(
                StockItem.product_id
                == product["id"],
                StockItem.warehouse_id
                == warehouse["id"],
            )
        )
    ).scalar_one()

    assert dec(
        stock.quantity_on_hand
    ) == Decimal("8.000")


@pytest.mark.asyncio
async def test_service_part_insufficient_stock_rejected(
    client,
    admin_headers,
    db_session,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="306",
    )

    product = await create_product(
        client,
        admin_headers,
        db_session,
        suffix="306",
        serialized=False,
    )

    warehouse = await get_warehouse(
        client,
        admin_headers,
    )

    received = await receive_non_serialized(
        client,
        admin_headers,
        product_id=product["id"],
        warehouse_id=warehouse["id"],
        quantity="1.000",
        unit_cost="100.00",
        reference_id="SERVICE-OPEN-306",
    )

    assert received.status_code == 201

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="306",
        product_id=product["id"],
    )

    await move_to_approved(
        client,
        admin_headers,
        job["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{job['id']}/parts",
        headers=admin_headers,
        json={
            "product_id":
                product["id"],
            "warehouse_id":
                warehouse["id"],
            "quantity":
                "2.000",
        },
    )

    assert response.status_code == 409

    detail = response.json()["detail"]

    assert (
        detail["message"]
        == (
            "Insufficient available stock "
            "for service issue"
        )
    )


@pytest.mark.asyncio
async def test_ready_requires_testing_result(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="307",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="307",
    )

    await move_to_testing(
        client,
        admin_headers,
        job["id"],
    )

    response = await change_status(
        client,
        admin_headers,
        job["id"],
        "ready",
    )

    assert response.status_code == 409

    assert (
        response.json()["detail"]
        == (
            "Testing result is required before "
            "marking a job as ready"
        )
    )


@pytest.mark.asyncio
async def test_service_invoice_full_flow_and_duplicate_guard(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="308",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="308",
    )

    await move_to_inspection(
        client,
        admin_headers,
        job["id"],
    )

    labour = await client.post(
        f"{BASE_URL}/{job['id']}/labour",
        headers=admin_headers,
        json={
            "description":
                "Repair labour",
            "hours":
                "2.00",
            "amount":
                "4000.00",
        },
    )

    assert labour.status_code == 201

    waiting = await change_status(
        client,
        admin_headers,
        job["id"],
        "waiting_approval",
    )

    assert waiting.status_code == 200

    approval = await client.post(
        f"{BASE_URL}/{job['id']}/approval",
        headers=admin_headers,
        json={
            "approval_status":
                "approved",
        },
    )

    assert approval.status_code == 200

    repairing = await change_status(
        client,
        admin_headers,
        job["id"],
        "repairing",
    )

    assert repairing.status_code == 200

    testing = await change_status(
        client,
        admin_headers,
        job["id"],
        "testing",
    )

    assert testing.status_code == 200

    update = await client.patch(
        f"{BASE_URL}/{job['id']}",
        headers=admin_headers,
        json={
            "testing_result":
                "Unit passed final test",
            "work_performed":
                "Component repaired",
        },
    )

    assert update.status_code == 200

    ready = await change_status(
        client,
        admin_headers,
        job["id"],
        "ready",
    )

    assert ready.status_code == 200

    invoice_response = await client.post(
        f"{BASE_URL}/{job['id']}/invoice",
        headers=admin_headers,
    )

    assert invoice_response.status_code == 201, (
        invoice_response.text
    )

    invoice = invoice_response.json()

    assert invoice["invoice_number"].startswith(
        "INV-"
    )
    assert invoice["invoice_status"] == "draft"
    assert invoice["payment_status"] == "unpaid"
    assert invoice["source_type"] == "service_job"
    assert invoice["source_id"] == job["id"]

    assert dec(
        invoice["subtotal"]
    ) == Decimal("4000.00")

    assert dec(
        invoice["grand_total"]
    ) == Decimal("4000.00")

    assert len(invoice["items"]) == 1

    refreshed = await client.get(
        f"{BASE_URL}/{job['id']}",
        headers=admin_headers,
    )

    assert refreshed.status_code == 200

    assert (
        refreshed.json()["related_invoice_id"]
        == invoice["id"]
    )

    duplicate = await client.post(
        f"{BASE_URL}/{job['id']}/invoice",
        headers=admin_headers,
    )

    assert duplicate.status_code == 409

    assert (
        "already has invoice"
        in duplicate.json()["detail"]
    )


@pytest.mark.asyncio
async def test_service_invoice_without_billables_rejected(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="309",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="309",
    )

    await move_to_ready(
        client,
        admin_headers,
        job["id"],
    )

    response = await client.post(
        f"{BASE_URL}/{job['id']}/invoice",
        headers=admin_headers,
    )

    assert response.status_code == 409

    assert (
        response.json()["detail"]
        == (
            "Service job has no billable "
            "parts or labour"
        )
    )


@pytest.mark.asyncio
async def test_warranty_job_without_serial_requires_manual_verification(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="310",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="310",
        is_warranty_job=True,
    )

    assert job["is_warranty_job"] is True
    assert job["service_type"] == "warranty"
    assert job["warranty_verified"] is False

    assert (
        "Manual verification required"
        in job["warranty_notes"]
    )

    response = await client.get(
        BASE_URL,
        headers=admin_headers,
        params={
            "warranty_only":
                "true",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert (
        data["items"][0]["id"]
        == job["id"]
    )


@pytest.mark.asyncio
async def test_delivered_job_cannot_be_edited(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="311",
    )

    job = await create_job(
        client,
        admin_headers,
        customer_id=customer["id"],
        suffix="311",
    )

    await move_to_ready(
        client,
        admin_headers,
        job["id"],
    )

    delivered = await change_status(
        client,
        admin_headers,
        job["id"],
        "delivered",
        remarks="Returned to customer",
    )

    assert delivered.status_code == 200

    assert (
        delivered.json()["status"]
        == "delivered"
    )

    assert (
        delivered.json()["delivered_at"]
        is not None
    )

    response = await client.patch(
        f"{BASE_URL}/{job['id']}",
        headers=admin_headers,
        json={
            "special_notes":
                "Should not be accepted",
        },
    )

    assert response.status_code == 409

    assert (
        response.json()["detail"]
        == (
            "Delivered or cancelled job cards "
            "cannot be edited"
        )
    )


@pytest.mark.asyncio
async def test_service_job_scheduled_visit_date_lifecycle(
    client,
    admin_headers,
):
    customer = await create_customer(
        client,
        admin_headers,
        suffix="912",
    )

    create_payload = {
        "customer_id":
            customer["id"],
        "complaint":
            "Scheduled visit lifecycle test",
        "scheduled_visit_date":
            "2026-08-15",
        "service_type":
            "repair",
        "priority":
            "normal",
        "estimated_cost":
            "0.00",
    }

    create_response = await client.post(
        BASE_URL,
        json=create_payload,
        headers=admin_headers,
    )

    assert create_response.status_code == 201, (
        create_response.text
    )

    created = create_response.json()

    assert (
        created["scheduled_visit_date"]
        == "2026-08-15"
    )

    job_id = created["id"]

    read_response = await client.get(
        f"{BASE_URL}/{job_id}",
        headers=admin_headers,
    )

    assert read_response.status_code == 200, (
        read_response.text
    )

    assert (
        read_response.json()[
            "scheduled_visit_date"
        ]
        == "2026-08-15"
    )

    update_response = await client.patch(
        f"{BASE_URL}/{job_id}",
        json={
            "scheduled_visit_date":
                "2026-08-16",
        },
        headers=admin_headers,
    )

    assert update_response.status_code == 200, (
        update_response.text
    )

    assert (
        update_response.json()[
            "scheduled_visit_date"
        ]
        == "2026-08-16"
    )

    final_response = await client.get(
        f"{BASE_URL}/{job_id}",
        headers=admin_headers,
    )

    assert final_response.status_code == 200, (
        final_response.text
    )

    assert (
        final_response.json()[
            "scheduled_visit_date"
        ]
        == "2026-08-16"
    )
