from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.seed_data import seed_system_data
from app.db.seed_inventory import seed_inventory_data
from app.db.session import AsyncSessionLocal
from app.models import User, UserRole


settings = get_settings()


async def create_initial_admin(
    session: AsyncSession,
) -> None:
    username = (
        settings.initial_admin_username
        .strip()
        .lower()
    )

    email = (
        settings.initial_admin_email
        .strip()
        .lower()
    )

    result = await session.execute(
        select(User).where(
            or_(
                User.username == username,
                User.email == email,
            )
        )
    )

    existing_user = (
        result.scalar_one_or_none()
    )

    if existing_user is not None:
        return

    admin = User(
        username=username,
        email=email,
        full_name=(
            settings.initial_admin_full_name
            .strip()
        ),
        hashed_password=hash_password(
            settings.initial_admin_password
        ),
        role=UserRole.SUPER_ADMIN.value,
        is_active=True,
        is_superuser=True,
    )

    session.add(admin)
    await session.commit()


async def initialize_database() -> None:
    async with AsyncSessionLocal() as session:
        if settings.startup_seed_enabled:
            await seed_system_data(
                session
            )

            await seed_inventory_data(
                session
            )

        if (
            settings
            .startup_create_admin_enabled
        ):
            await create_initial_admin(
                session
            )
