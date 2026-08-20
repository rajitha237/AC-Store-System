from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable
from typing import Any

import asyncpg
from sqlalchemy.engine import make_url


AsyncConnectionCreator = Callable[
    [],
    Awaitable[Any],
]


def _database_url(
    database_url: str,
):
    return make_url(
        database_url
    )


def database_hostname(
    database_url: str,
) -> str | None:
    return _database_url(
        database_url
    ).host


def should_use_neon_ipv4_creator(
    database_url: str,
) -> bool:
    url = _database_url(
        database_url
    )

    hostname = url.host

    if hostname is None:
        return False

    return (
        url.drivername
        == "postgresql+asyncpg"
        and hostname.lower().endswith(
            ".neon.tech"
        )
    )


async def _resolve_ipv4_addresses(
    hostname: str,
    port: int,
) -> list[str]:
    loop = asyncio.get_running_loop()

    results = await loop.getaddrinfo(
        hostname,
        port,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
    )

    addresses: list[str] = []

    for result in results:
        address = result[4][0]

        if address not in addresses:
            addresses.append(
                address
            )

    if not addresses:
        raise ConnectionError(
            "No IPv4 addresses resolved "
            "for database host"
        )

    return addresses


def build_neon_async_creator(
    database_url: str,
) -> AsyncConnectionCreator | None:
    if not should_use_neon_ipv4_creator(
        database_url
    ):
        return None

    url = _database_url(
        database_url
    )

    hostname = url.host
    username = url.username
    password = url.password
    database = url.database
    port = url.port or 5432

    if hostname is None:
        raise ValueError(
            "Database hostname is required"
        )

    if username is None:
        raise ValueError(
            "Database username is required"
        )

    if password is None:
        raise ValueError(
            "Database password is required"
        )

    if database is None:
        raise ValueError(
            "Database name is required"
        )

    endpoint_id = hostname.split(
        ".",
        1,
    )[0]

    ssl_mode = (
        url.query.get(
            "ssl",
            "require",
        )
    )

    async def connect():
        addresses = (
            await _resolve_ipv4_addresses(
                hostname,
                port,
            )
        )

        last_error: Exception | None = None

        for address in addresses:
            try:
                return await asyncpg.connect(
                    host=address,
                    port=port,
                    user=username,
                    password=password,
                    database=database,
                    ssl=ssl_mode,
                    timeout=15,
                    server_settings={
                        "options": (
                            f"endpoint={endpoint_id}"
                        ),
                    },
                )

            except Exception as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        raise ConnectionError(
            "Unable to connect to "
            "database IPv4 address"
        )

    return connect
