from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import Permission, Role, RolePermission, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db_session),
]

AccessToken = Annotated[
    str,
    Depends(oauth2_scheme),
]


async def get_current_user(
    session: DatabaseSession,
    token: AccessToken,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise credentials_exception

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive",
        )

    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]


async def require_superuser(
    current_user: CurrentUser,
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super administrator permission required",
        )

    return current_user


SuperUser = Annotated[
    User,
    Depends(require_superuser),
]


def require_permission(
    permission_code: str,
) -> Callable:
    async def permission_dependency(
        session: DatabaseSession,
        current_user: CurrentUser,
    ) -> User:
        if current_user.is_superuser:
            return current_user

        statement = (
            select(Permission.id)
            .join(
                RolePermission,
                RolePermission.permission_id
                == Permission.id,
            )
            .join(
                Role,
                Role.id == RolePermission.role_id,
            )
            .where(
                Role.code == current_user.role,
                Role.is_active.is_(True),
                Permission.code == permission_code,
            )
        )

        permission_id = await session.scalar(statement)

        if permission_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission required: "
                    f"{permission_code}"
                ),
            )

        return current_user

    return permission_dependency
