from __future__ import annotations

import json
from datetime import (
    date,
    datetime,
)
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    raise TypeError(
        f"Object of type "
        f"{type(value).__name__} "
        "is not JSON serializable"
    )


def serialize_audit_data(
    value: Any,
) -> str | None:
    if value is None:
        return None

    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


async def create_audit_log(
    session: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    module: str,
    entity_type: str,
    entity_id: int | None = None,
    entity_reference: str | None = None,
    description: str,
    before_data: Any = None,
    after_data: Any = None,
    metadata: Any = None,
    ip_address: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_reference=entity_reference,
        description=description,
        before_data=serialize_audit_data(
            before_data
        ),
        after_data=serialize_audit_data(
            after_data
        ),
        metadata_json=serialize_audit_data(
            metadata
        ),
        ip_address=ip_address,
    )

    session.add(audit_log)

    await session.flush()

    return audit_log


async def list_audit_logs(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    module: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    from math import ceil

    from sqlalchemy import (
        func,
        or_,
        select,
    )

    from app.models.user import User

    filters = []

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                AuditLog.action.ilike(
                    pattern
                ),
                AuditLog.module.ilike(
                    pattern
                ),
                AuditLog.entity_type.ilike(
                    pattern
                ),
                AuditLog.entity_reference.ilike(
                    pattern
                ),
                AuditLog.description.ilike(
                    pattern
                ),
                User.username.ilike(
                    pattern
                ),
                User.full_name.ilike(
                    pattern
                ),
            )
        )

    if module and module.strip():
        filters.append(
            AuditLog.module
            == module.strip()
        )

    if action and action.strip():
        filters.append(
            AuditLog.action
            == action.strip()
        )

    if entity_type and entity_type.strip():
        filters.append(
            AuditLog.entity_type
            == entity_type.strip()
        )

    if entity_id is not None:
        filters.append(
            AuditLog.entity_id
            == entity_id
        )

    if user_id is not None:
        filters.append(
            AuditLog.user_id
            == user_id
        )

    if date_from is not None:
        filters.append(
            AuditLog.created_at
            >= date_from
        )

    if date_to is not None:
        filters.append(
            AuditLog.created_at
            <= date_to
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .outerjoin(
                User,
                User.id
                == AuditLog.user_id,
            )
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(
            AuditLog,
            User.username,
            User.full_name,
        )
        .outerjoin(
            User,
            User.id
            == AuditLog.user_id,
        )
        .where(*filters)
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset(
            (page - 1)
            * page_size
        )
        .limit(page_size)
    )

    items = []

    for (
        audit_log,
        username,
        user_full_name,
    ) in result.all():
        items.append({
            "id":
                audit_log.id,
            "user_id":
                audit_log.user_id,
            "username":
                username,
            "user_full_name":
                user_full_name,
            "action":
                audit_log.action,
            "module":
                audit_log.module,
            "entity_type":
                audit_log.entity_type,
            "entity_id":
                audit_log.entity_id,
            "entity_reference":
                audit_log.entity_reference,
            "description":
                audit_log.description,
            "before_data":
                (
                    json.loads(
                        audit_log.before_data
                    )
                    if audit_log.before_data
                    else None
                ),
            "after_data":
                (
                    json.loads(
                        audit_log.after_data
                    )
                    if audit_log.after_data
                    else None
                ),
            "metadata":
                (
                    json.loads(
                        audit_log.metadata_json
                    )
                    if audit_log.metadata_json
                    else None
                ),
            "ip_address":
                audit_log.ip_address,
            "created_at":
                audit_log.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (
            ceil(total / page_size)
            if total
            else 0
        ),
    }
