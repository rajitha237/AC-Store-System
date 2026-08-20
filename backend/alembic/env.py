from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    async_engine_from_config,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base
from app.db.ipv4_resolver import (
    build_neon_async_creator,
)
from app.models import (
    AuditLog,
    Branch,
    Brand,
    Company,
    Customer,
    CustomerPayment,
    CreditNote,
    CustomerRefund,
    Permission,
    Product,
    ProductCategory,
    ProductSerialNumber,
    Role,
    RolePermission,
    SalesInvoice,
    SalesInvoiceItem,
    SalesReturn,
    SalesReturnItem,
    SalesReturnStatusHistory,
    ServiceChecklistItem,
    ServiceJobCard,
    ServiceJobImage,
    ServiceJobPart,
    ServiceJobStatusHistory,
    ServiceLabourItem,
    StockItem,
    StockMovement,
    Supplier,
    UnitOfMeasure,
    User,
    Warehouse,
)

config = context.config
settings = get_settings()

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    async_creator = build_neon_async_creator(
        settings.database_url,
    )

    if async_creator is not None:
        connectable = create_async_engine(
            settings.database_url,
            poolclass=pool.NullPool,
            async_creator=async_creator,
        )
    else:
        connectable = async_engine_from_config(
            config.get_section(
                config.config_ini_section,
                {},
            ),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    async with connectable.connect() as connection:
        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
