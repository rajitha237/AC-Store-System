import pytest


@pytest.mark.asyncio
async def test_admin_login(
    client,
):
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username":
                "admin@acstore.local",
            "password":
                "Admin@12345",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"

    assert data["access_token"]


@pytest.mark.asyncio
async def test_invalid_login_rejected(
    client,
):
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username":
                "admin@acstore.local",
            "password":
                "wrong-password",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/v1/auth/me",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "admin"

    assert (
        data["role"]
        == "super_admin"
    )

    assert (
        data["is_superuser"]
        is True
    )
