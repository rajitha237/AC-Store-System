from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DatabaseSession, SuperUser
from app.models import Permission, Role, RolePermission
from app.schemas.access_control import (
    PermissionResponse,
    RoleDetailResponse,
    RoleSummaryResponse,
)

router = APIRouter(
    prefix="/access-control",
    tags=["Access Control"],
)


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
)
async def list_permissions(
    session: DatabaseSession,
    _: SuperUser,
) -> list[PermissionResponse]:
    result = await session.execute(
        select(Permission).order_by(
            Permission.module,
            Permission.code,
        )
    )

    return [
        PermissionResponse.model_validate(permission)
        for permission in result.scalars().all()
    ]


@router.get(
    "/roles",
    response_model=list[RoleSummaryResponse],
)
async def list_roles(
    session: DatabaseSession,
    _: SuperUser,
) -> list[RoleSummaryResponse]:
    statement = (
        select(
            Role,
            func.count(RolePermission.id).label(
                "permission_count"
            ),
        )
        .outerjoin(
            RolePermission,
            RolePermission.role_id == Role.id,
        )
        .group_by(Role.id)
        .order_by(Role.name)
    )

    result = await session.execute(statement)

    return [
        RoleSummaryResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permission_count=permission_count,
        )
        for role, permission_count in result.all()
    ]


@router.get(
    "/roles/{role_id}",
    response_model=RoleDetailResponse,
)
async def read_role(
    role_id: int,
    session: DatabaseSession,
    _: SuperUser,
) -> RoleDetailResponse:
    result = await session.execute(
        select(Role)
        .options(
            selectinload(Role.permission_links).selectinload(
                RolePermission.permission
            )
        )
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role record was not found",
        )

    permissions = sorted(
        (
            link.permission
            for link in role.permission_links
        ),
        key=lambda permission: (
            permission.module,
            permission.code,
        ),
    )

    return RoleDetailResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=[
            PermissionResponse.model_validate(permission)
            for permission in permissions
        ],
    )
