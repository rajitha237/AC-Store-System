from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.technician_location import (
    CompletedServiceJobLocationResponse,
    TechnicianLocationAdminResponse,
    TechnicianLocationResponse,
    TechnicianLocationUpdateRequest,
)
from app.services.technician_location import (
    list_completed_service_job_locations,
    list_technician_locations,
    update_own_technician_location,
)


router = APIRouter(
    prefix="/service",
    tags=[
        "Field Service Location"
    ],
)


CanUseFieldService = Annotated[
    User,
    Depends(
        require_permission(
            "job_cards.view"
        )
    ),
]


@router.post(
    "/technician/location",
    response_model=(
        TechnicianLocationResponse
    ),
)
async def write_technician_location(
    payload:
        TechnicianLocationUpdateRequest,
    session: DatabaseSession,
    current_user:
        CanUseFieldService,
) -> TechnicianLocationResponse:
    return (
        await
        update_own_technician_location(
            session,
            payload=payload,
            current_user=current_user,
        )
    )


@router.get(
    "/technicians/locations",
    response_model=list[
        TechnicianLocationAdminResponse
    ],
)
async def read_technician_locations(
    session: DatabaseSession,
    current_user:
        CanUseFieldService,
) -> list[
    TechnicianLocationAdminResponse
]:
    return (
        await
        list_technician_locations(
            session,
            current_user=current_user,
        )
    )


@router.get(
    "/jobs/completed/locations",
    response_model=list[
        CompletedServiceJobLocationResponse
    ],
)
async def read_completed_service_job_locations(
    session: DatabaseSession,
    current_user: CanUseFieldService,
) -> list[CompletedServiceJobLocationResponse]:
    if str(current_user.role) == "technician":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Completed job location map "
                "is for service management only"
            ),
        )

    return await list_completed_service_job_locations(
        session
    )
