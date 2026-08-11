from datetime import timedelta
import uuid

import pytest
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    hash_password,
)
from app.models import Role, User


PROTECTED_ROUTE = "/api/v1/customers"


async def create_security_user(
    db_session,
    *,
    role="technician",
    is_active=True,
    is_superuser=False,
):
    unique = uuid.uuid4().hex[:12]

    user = User(
        username=f"security_{unique}",
        email=f"security_{unique}@test.local",
        full_name=f"Security Test {unique}",
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


def bearer(token):
    return {
        "Authorization":
            f"Bearer {token}",
    }


def token_for_user(
    user,
    **kwargs,
):
    return create_access_token(
        subject=str(user.id),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_expired_access_token_rejected(
    client,
    db_session,
):
    user = await create_security_user(
        db_session
    )

    token = token_for_user(
        user,
        expires_delta=timedelta(
            seconds=-1
        ),
    )

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401

    data = response.json()

    assert (
        data["detail"]
        == (
            "Invalid or expired "
            "authentication credentials"
        )
    )

    assert (
        response.headers.get(
            "www-authenticate"
        )
        == "Bearer"
    )


@pytest.mark.asyncio
async def test_wrong_token_type_rejected(
    client,
    db_session,
):
    user = await create_security_user(
        db_session
    )

    token = token_for_user(
        user,
        extra_claims={
            "type":
                "refresh",
        },
    )

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == (
            "Invalid or expired "
            "authentication credentials"
        )
    )


@pytest.mark.asyncio
async def test_missing_token_subject_rejected(
    client,
):
    token = create_access_token(
        subject=""
    )

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == (
            "Invalid or expired "
            "authentication credentials"
        )
    )


@pytest.mark.asyncio
async def test_non_numeric_token_subject_rejected(
    client,
):
    token = create_access_token(
        subject="not-a-user-id"
    )

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_for_nonexistent_user_rejected(
    client,
):
    token = create_access_token(
        subject="999999999"
    )

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == (
            "Invalid or expired "
            "authentication credentials"
        )
    )


@pytest.mark.asyncio
async def test_token_for_deleted_user_rejected(
    client,
    db_session,
):
    user = await create_security_user(
        db_session
    )

    token = token_for_user(user)

    await db_session.delete(user)
    await db_session.commit()

    response = await client.get(
        PROTECTED_ROUTE,
        headers=bearer(token),
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_role_blocks_existing_permission(
    client,
    db_session,
):
    role = (
        await db_session.execute(
            select(Role)
            .where(
                Role.code == "technician"
            )
        )
    ).scalar_one()

    assert role.is_active is True

    role.is_active = False

    await db_session.commit()

    user = await create_security_user(
        db_session,
        role="technician",
    )

    token = token_for_user(user)

    response = await client.get(
        "/api/v1/customers",
        headers=bearer(token),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "Permission required: "
            "customers.view"
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "method",
        "path",
        "payload",
        "permission",
    ),
    [
        (
            "POST",
            "/api/v1/customers",
            {},
            "customers.create",
        ),
        (
            "POST",
            "/api/v1/inventory/receive/non-serialized",
            {},
            "inventory.receive",
        ),
        (
            "POST",
            "/api/v1/sales/invoices",
            {},
            "sales.create",
        ),
        (
            "POST",
            "/api/v1/returns",
            {},
            "returns.create",
        ),
    ],
)
async def test_technician_cannot_use_sensitive_write_routes(
    client,
    db_session,
    method,
    path,
    payload,
    permission,
):
    user = await create_security_user(
        db_session,
        role="technician",
    )

    token = token_for_user(user)

    response = await client.request(
        method,
        path,
        headers=bearer(token),
        json=payload,
    )

    assert response.status_code == 403, (
        f"{method} {path}: "
        f"{response.status_code} "
        f"{response.text}"
    )

    assert (
        response.json()["detail"]
        == f"Permission required: {permission}"
    )


@pytest.mark.asyncio
async def test_non_superuser_cannot_enumerate_permissions(
    client,
    db_session,
):
    user = await create_security_user(
        db_session,
        role="manager",
    )

    response = await client.get(
        "/api/v1/access-control/permissions",
        headers=bearer(
            token_for_user(user)
        ),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "Super administrator "
            "permission required"
        )
    )


@pytest.mark.asyncio
async def test_superuser_bypasses_role_permission_lookup(
    client,
    db_session,
):
    user = await create_security_user(
        db_session,
        role="technician",
        is_superuser=True,
    )

    response = await client.get(
        "/api/v1/audit-logs",
        headers=bearer(
            token_for_user(user)
        ),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_inactive_superuser_account_still_rejected(
    client,
    db_session,
):
    user = await create_security_user(
        db_session,
        role="super_admin",
        is_active=False,
        is_superuser=True,
    )

    response = await client.get(
        "/api/v1/access-control/roles",
        headers=bearer(
            token_for_user(user)
        ),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "This user account is inactive"
    )


def test_only_expected_routes_are_public(
    client,
):
    schema = client._transport.app.openapi()

    public = set()

    for path, operations in (
        schema.get(
            "paths",
            {},
        ).items()
    ):
        for method, operation in (
            operations.items()
        ):
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                continue

            if not operation.get(
                "security"
            ):
                public.add(
                    (
                        method.upper(),
                        path,
                    )
                )

    assert public == {
        (
            "GET",
            "/",
        ),
        (
            "GET",
            "/api/v1/health",
        ),
        (
            "POST",
            "/api/v1/auth/login",
        ),
    }


@pytest.mark.asyncio
async def test_auth_me_does_not_trust_role_claim_from_token(
    client,
    db_session,
):
    user = await create_security_user(
        db_session,
        role="technician",
    )

    token = token_for_user(
        user,
        extra_claims={
            "role":
                "super_admin",
            "username":
                "fake-admin",
        },
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers=bearer(token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == user.id
    assert data["role"] == "technician"
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_forged_role_claim_does_not_grant_superuser_access(
    client,
    db_session,
):
    user = await create_security_user(
        db_session,
        role="technician",
    )

    token = token_for_user(
        user,
        extra_claims={
            "role":
                "super_admin",
            "is_superuser":
                True,
        },
    )

    response = await client.get(
        "/api/v1/access-control/roles",
        headers=bearer(token),
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == (
            "Super administrator "
            "permission required"
        )
    )
