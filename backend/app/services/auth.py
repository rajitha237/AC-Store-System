from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User


async def get_user_by_login(
    session: AsyncSession,
    login: str,
) -> User | None:
    normalized_login = login.strip().lower()

    statement = select(User).where(
        or_(
            User.username == normalized_login,
            User.email == normalized_login,
        )
    )

    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    login: str,
    password: str,
) -> User | None:
    user = await get_user_by_login(
        session=session,
        login=login,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        plain_password=password,
        hashed_password=user.hashed_password,
    ):
        return None

    user.last_login_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(user)

    return user
