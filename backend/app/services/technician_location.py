from datetime import (
    datetime,
    timezone,
)

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.models import (
    ServiceJobCard,
    ServiceJobLocationRecord,
    TechnicianLocation,
    User,
)
from app.schemas.technician_location import (
    CompletedServiceJobLocationResponse,
    TechnicianLocationAdminResponse,
    TechnicianLocationResponse,
    TechnicianLocationUpdateRequest,
)
from app.services.service import (
    ensure_technician_job_access,
    get_job_card,
)


LOCATION_LIVE_SECONDS = 300


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def is_technician_user(
    user: User,
) -> bool:
    return (
        str(user.role)
        == "technician"
    )


def location_presence_status(
    location: TechnicianLocation,
    *,
    now: datetime,
) -> tuple[str, int]:
    recorded_at = (
        location.recorded_at
    )

    if (
        recorded_at.tzinfo
        is None
    ):
        recorded_at = (
            recorded_at.replace(
                tzinfo=timezone.utc,
            )
        )

    age_seconds = max(
        0,
        int(
            (
                now
                - recorded_at
            ).total_seconds()
        ),
    )

    if (
        location.tracking_state
        == "stopped"
    ):
        return (
            "offline",
            age_seconds,
        )

    if (
        age_seconds
        <= LOCATION_LIVE_SECONDS
    ):
        return (
            "live",
            age_seconds,
        )

    return (
        "stale",
        age_seconds,
    )


async def update_own_technician_location(
    session: AsyncSession,
    *,
    payload:
        TechnicianLocationUpdateRequest,
    current_user: User,
) -> TechnicianLocationResponse:
    if not is_technician_user(
        current_user
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Technician account "
                "required"
            ),
        )

    if (
        not current_user.is_active
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Technician account "
                "is inactive"
            ),
        )

    if (
        payload.service_job_id
        is not None
    ):
        job = await get_job_card(
            session,
            payload.service_job_id,
        )

        ensure_technician_job_access(
            job,
            current_user,
        )

    result = await session.execute(
        select(
            TechnicianLocation
        ).where(
            TechnicianLocation
            .technician_id
            == current_user.id
        )
    )

    location = (
        result
        .scalar_one_or_none()
    )

    now = utc_now()

    if location is None:
        location = (
            TechnicianLocation(
                technician_id=(
                    current_user.id
                ),
                service_job_id=(
                    payload
                    .service_job_id
                ),
                latitude=(
                    payload.latitude
                ),
                longitude=(
                    payload.longitude
                ),
                accuracy_meters=(
                    payload
                    .accuracy_meters
                ),
                client_recorded_at=(
                    payload
                    .client_recorded_at
                ),
                recorded_at=now,
                tracking_state=(
                    payload
                    .tracking_state
                ),
                source=(
                    "technician_web_portal"
                ),
            )
        )

        session.add(
            location
        )

    else:
        location.service_job_id = (
            payload.service_job_id
        )

        if (
            payload.latitude
            is not None
        ):
            location.latitude = (
                payload.latitude
            )

            location.longitude = (
                payload.longitude
            )

        if (
            payload.accuracy_meters
            is not None
        ):
            (
                location
                .accuracy_meters
            ) = (
                payload
                .accuracy_meters
            )

        location.client_recorded_at = (
            payload
            .client_recorded_at
        )

        location.recorded_at = now

        location.tracking_state = (
            payload.tracking_state
        )

        location.source = (
            "technician_web_portal"
        )

    try:
        await session.commit()

        await session.refresh(
            location
        )

    except Exception:
        await session.rollback()
        raise

    return (
        TechnicianLocationResponse
        .model_validate(
            location
        )
    )


async def list_technician_locations(
    session: AsyncSession,
    *,
    current_user: User,
) -> list[
    TechnicianLocationAdminResponse
]:
    if is_technician_user(
        current_user
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Technicians cannot "
                "view team locations"
            ),
        )

    result = await session.execute(
        select(
            TechnicianLocation,
            User.full_name,
            ServiceJobCard.job_number,
        )
        .join(
            User,
            User.id
            == TechnicianLocation
            .technician_id,
        )
        .outerjoin(
            ServiceJobCard,
            ServiceJobCard.id
            == TechnicianLocation
            .service_job_id,
        )
        .where(
            User.role
            == "technician",
            User.is_active.is_(
                True
            ),
        )
        .order_by(
            User.full_name.asc(),
        )
    )

    now = utc_now()

    response: list[
        TechnicianLocationAdminResponse
    ] = []

    for (
        location,
        technician_name,
        service_job_number,
    ) in result.all():
        (
            presence_status,
            age_seconds,
        ) = location_presence_status(
            location,
            now=now,
        )

        response.append(
            TechnicianLocationAdminResponse(
                id=location.id,
                technician_id=(
                    location
                    .technician_id
                ),
                technician_name=(
                    technician_name
                ),
                service_job_id=(
                    location
                    .service_job_id
                ),
                service_job_number=(
                    service_job_number
                ),
                latitude=(
                    location.latitude
                ),
                longitude=(
                    location.longitude
                ),
                accuracy_meters=(
                    location
                    .accuracy_meters
                ),
                client_recorded_at=(
                    location
                    .client_recorded_at
                ),
                recorded_at=(
                    location.recorded_at
                ),
                tracking_state=(
                    location
                    .tracking_state
                ),
                source=(
                    location.source
                ),
                presence_status=(
                    presence_status
                ),
                age_seconds=(
                    age_seconds
                ),
            )
        )

    return response


async def list_completed_service_job_locations(
    session: AsyncSession,
) -> list[CompletedServiceJobLocationResponse]:
    result = await session.execute(
        select(
            ServiceJobLocationRecord,
            ServiceJobCard.job_number,
            User.full_name,
        )
        .join(
            ServiceJobCard,
            ServiceJobCard.id
            == ServiceJobLocationRecord.service_job_id,
        )
        .join(
            User,
            User.id
            == ServiceJobLocationRecord.technician_id,
        )
        .order_by(
            ServiceJobLocationRecord.completed_at.desc(),
            ServiceJobLocationRecord.id.desc(),
        )
    )

    records: list[
        CompletedServiceJobLocationResponse
    ] = []

    for (
        location,
        job_number,
        technician_name,
    ) in result.all():
        records.append(
            CompletedServiceJobLocationResponse(
                id=location.id,
                service_job_id=(
                    location.service_job_id
                ),
                service_job_number=(
                    job_number
                    or f"JOB-{location.service_job_id}"
                ),
                technician_id=(
                    location.technician_id
                ),
                technician_name=(
                    technician_name
                    or (
                        "Technician "
                        f"#{location.technician_id}"
                    )
                ),
                latitude=location.latitude,
                longitude=location.longitude,
                accuracy_meters=(
                    location.accuracy_meters
                ),
                completed_at=(
                    location.completed_at
                ),
                recorded_at=(
                    location.recorded_at
                ),
            )
        )

    return records
