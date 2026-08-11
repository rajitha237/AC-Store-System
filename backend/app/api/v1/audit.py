from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.audit import (
    AuditLogListResponse,
)
from app.services.audit import (
    list_audit_logs,
)


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


CanViewAuditLogs = Annotated[
    User,
    Depends(
        require_permission("audit.view")
    ),
]


@router.get(
    "",
    response_model=AuditLogListResponse,
)
async def read_audit_logs(
    session: DatabaseSession,
    _: CanViewAuditLogs,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    module: str | None = Query(
        default=None,
        max_length=100,
    ),
    action: str | None = Query(
        default=None,
        max_length=100,
    ),
    entity_type: str | None = Query(
        default=None,
        max_length=100,
    ),
    entity_id: int | None = Query(
        default=None,
        ge=1,
    ),
    user_id: int | None = Query(
        default=None,
        ge=1,
    ),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AuditLogListResponse:
    result = await list_audit_logs(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        module=module,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    return AuditLogListResponse(
        **result
    )
