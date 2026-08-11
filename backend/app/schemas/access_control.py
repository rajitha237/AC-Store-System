from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    module: str
    name: str
    description: str | None
    created_at: datetime


class RoleSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permission_count: int


class RoleDetailResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse]
