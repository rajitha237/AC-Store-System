from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.sms_notifications import (
    SmsNotificationListResponse,
)
from app.services.cash_book import (
    get_active_cash_book_company,
)
from app.services.sms_notifications import (
    list_sms_notifications,
)


router = APIRouter(
    prefix="/sms-center",
    tags=["SMS Center"],
)


CanViewSmsCenter = Annotated[
    User,
    Depends(
        require_permission(
            "audit.view"
        )
    ),
]


async def _active_company(
    session: DatabaseSession,
):
    try:
        return (
            await get_active_cash_book_company(
                session
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=(
        SmsNotificationListResponse
    ),
)
async def read_sms_notifications(
    session: DatabaseSession,
    _: CanViewSmsCenter,
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
    status_filter: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),
    recipient_type: str | None = Query(
        default=None,
        max_length=30,
    ),
    event_type: str | None = Query(
        default=None,
        max_length=60,
    ),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> SmsNotificationListResponse:
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "date_from cannot be "
                "after date_to"
            ),
        )

    company = await _active_company(
        session
    )

    result = (
        await list_sms_notifications(
            session,
            company_id=company.id,
            timezone_name=company.timezone,
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
            recipient_type=recipient_type,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
        )
    )

    return SmsNotificationListResponse(
        **result
    )
