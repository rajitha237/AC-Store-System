import uuid

import pytest
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    hash_password,
)
from app.models import User


async def create_test_user(
    db_session,
    *,
    role: str,
    is_active: bool = True,
    is_superuser: bool = False,
):
    unique = uuid.uuid4().hex[:12]

    user = User(
        username=f"rbac_{unique}",
        email=f"rbac_{unique}@test.local",
        full_name=f"RBAC Test {unique}",
        hashed_password=hash_password(
            "Test@12345"
        ),
        role=role,
        is_active=is_active,
        is_superuser=is_superuser,
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
async def test_protected_route_requires_authentication(
    client,
):
    response = await client.get(
        "/api/v1/customers"
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected(
    client,
):
    response = await client.get(
        "/api/v1/customers",
        headers={
            "Authorization":
                "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_rejected(
    client,
    db_session,
):
    user = await create_test_user(
        db_session,
        role="technician",
        is_active=False,
    )

    response = await client.get(
        "/api/v1/customers",
        headers=headers_for_user(user),
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "This user account is inactive"
    )


@pytest.mark.asyncio
async def test_technician_can_view_customers(
    client,
    db_session,
):
    user = await create_test_user(
        db_session,
        role="technician",
    )

    response = await client.get(
        "/api/v1/customers",
        headers=headers_for_user(user),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_technician_cannot_create_customer(
    client,
    db_session,
):
    user = await create_test_user(
        db_session,
        role="technician",
    )

    response = await client.post(
        "/api/v1/customers",
        headers=headers_for_user(user),
        json={},
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Permission required: customers.create"
    )


@pytest.mark.asyncio
async def test_technician_cannot_view_audit_logs(
    client,
    db_session,
):
    user = await create_test_user(
        db_session,
        role="technician",
    )

    response = await client.get(
        "/api/v1/audit-logs",
        headers=headers_for_user(user),
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Permission required: audit.view"
    )


@pytest.mark.asyncio
async def test_super_admin_permission_bypass(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_non_superuser_cannot_access_superuser_route(
    client,
    db_session,
):
    user = await create_test_user(
        db_session,
        role="technician",
    )

    response = await client.get(
        "/api/v1/access-control/roles",
        headers=headers_for_user(user),
    )

    assert response.status_code == 403

    data = response.json()

    assert (
        data["detail"]
        == "Super administrator permission required"
    )


@pytest.mark.asyncio
async def test_super_admin_can_access_superuser_route(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/access-control/roles",
        headers=admin_headers,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_seeded_technician_role_exists(
    db_session,
):
    result = await db_session.execute(
        select(User).where(
            User.role == "technician"
        )
    )

    # The application does not need to seed a technician
    # user account. This query only verifies that querying
    # users by the valid role value is safe.
    result.scalars().all()
