from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)


def parse_json_field(
    value: Any,
) -> Any:
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    user_id: int | None
    username: str | None = None
    user_full_name: str | None = None

    action: str
    module: str

    entity_type: str
    entity_id: int | None
    entity_reference: str | None

    description: str

    before_data: Any = None
    after_data: Any = None
    metadata: Any = None

    ip_address: str | None

    created_at: datetime

    @field_validator(
        "before_data",
        "after_data",
        mode="before",
    )
    @classmethod
    def deserialize_json_fields(
        cls,
        value: Any,
    ) -> Any:
        return parse_json_field(value)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]

    total: int
    page: int
    page_size: int
    total_pages: int
