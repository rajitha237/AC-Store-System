from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.models.service import (
    ServiceJobPriority,
    ServiceJobStatus,
    ServiceType,
)
from app.schemas.sales import (
    SalesInvoiceDetailResponse,
)
from app.schemas.service import (
    ServiceApprovalRequest,
    ServiceJobCreate,
    ServiceJobDetailResponse,
    ServiceJobListResponse,
    ServiceJobUpdate,
    ServiceLabourCreate,
    ServicePartCreate,
    ServiceStatusChangeRequest,
)
from app.services.sales_service import (
    create_service_job_invoice,
    invoice_detail_response,
)
from app.services.service import (
    add_service_labour,
    add_service_part,
    build_job_detail,
    change_job_status,
    create_job_card,
    get_job_card,
    list_job_cards,
    update_approval,
    update_job_card,
)


router = APIRouter(
    prefix="/service",
    tags=["Service Center"],
)


CanViewJobs = Annotated[
    User,
    Depends(
        require_permission(
            "job_cards.view"
        )
    ),
]


CanCreateJobs = Annotated[
    User,
    Depends(
        require_permission(
            "job_cards.create"
        )
    ),
]


CanUpdateJobs = Annotated[
    User,
    Depends(
        require_permission(
            "job_cards.update"
        )
    ),
]


@router.post(
    "/jobs",
    response_model=ServiceJobDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_job(
    payload: ServiceJobCreate,
    session: DatabaseSession,
    current_user: CanCreateJobs,
) -> ServiceJobDetailResponse:
    job = await create_job_card(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)


@router.get(
    "/jobs",
    response_model=ServiceJobListResponse,
)
async def read_service_jobs(
    session: DatabaseSession,
    _: CanViewJobs,
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
    job_status: ServiceJobStatus | None = None,
    service_type: ServiceType | None = None,
    priority: ServiceJobPriority | None = None,
    technician_id: int | None = Query(
        default=None,
        ge=1,
    ),
    customer_id: int | None = Query(
        default=None,
        ge=1,
    ),
    warranty_only: bool = False,
) -> ServiceJobListResponse:
    return await list_job_cards(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        job_status=(
            job_status.value
            if job_status is not None
            else None
        ),
        service_type=(
            service_type.value
            if service_type is not None
            else None
        ),
        priority=(
            priority.value
            if priority is not None
            else None
        ),
        technician_id=technician_id,
        customer_id=customer_id,
        warranty_only=warranty_only,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ServiceJobDetailResponse,
)
async def read_service_job(
    job_id: int,
    session: DatabaseSession,
    _: CanViewJobs,
) -> ServiceJobDetailResponse:
    job = await get_job_card(
        session,
        job_id,
    )

    return await build_job_detail(job)


@router.patch(
    "/jobs/{job_id}",
    response_model=ServiceJobDetailResponse,
)
async def patch_service_job(
    job_id: int,
    payload: ServiceJobUpdate,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await update_job_card(
        session=session,
        job_id=job_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)


@router.post(
    "/jobs/{job_id}/status",
    response_model=ServiceJobDetailResponse,
)
async def update_service_job_status(
    job_id: int,
    payload: ServiceStatusChangeRequest,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await change_job_status(
        session=session,
        job_id=job_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)


@router.post(
    "/jobs/{job_id}/approval",
    response_model=ServiceJobDetailResponse,
)
async def update_service_job_approval(
    job_id: int,
    payload: ServiceApprovalRequest,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await update_approval(
        session=session,
        job_id=job_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)


@router.post(
    "/jobs/{job_id}/parts",
    response_model=ServiceJobDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_part_to_service_job(
    job_id: int,
    payload: ServicePartCreate,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await add_service_part(
        session=session,
        job_id=job_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)


@router.post(
    "/jobs/{job_id}/labour",
    response_model=ServiceJobDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_labour_to_service_job(
    job_id: int,
    payload: ServiceLabourCreate,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await add_service_labour(
        session=session,
        job_id=job_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_job_detail(job)

@router.post(
    "/jobs/{job_id}/invoice",
    response_model=SalesInvoiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_for_service_job(
    job_id: int,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> SalesInvoiceDetailResponse:
    invoice = await create_service_job_invoice(
        session=session,
        job_id=job_id,
        current_user=current_user,
    )

    return await invoice_detail_response(
        session,
        invoice,
    )

