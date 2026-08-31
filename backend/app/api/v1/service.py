from typing import Annotated

from sqlalchemy import select
from pydantic import BaseModel

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
from app.models import User, UserRole
from app.models.service import (
    ServiceJobPriority,
    ServiceJobStatus,
    ServiceType,
)
from app.schemas.sales import (
    SalesInvoiceDetailResponse,
    ServiceInvoiceCreateRequest,
)
from app.schemas.service import (
    ServiceApprovalRequest,
    ServiceJobCreate,
    ServiceJobCompleteRequest,
    ServiceJobDetailResponse,
    ServiceJobListResponse,
    ServiceJobUpdate,
    ServiceLabourCreate,
    ServicePartCreate,
    ServiceStatusChangeRequest,
    LegacyServiceJobStatusUpdateRequest,
    LegacyServiceJobStatusUpdateResponse,
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
    complete_service_job,
    create_job_card,
    delete_service_job,
    get_job_card,
    ensure_technician_job_access,
    list_job_cards,
    update_approval,
    update_job_card,
)


class TechnicianDirectoryItem(BaseModel):
    id: int
    username: str
    full_name: str


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


@router.get(
    "/technicians",
    response_model=list[TechnicianDirectoryItem],
)
async def list_service_technicians(
    session: DatabaseSession,
    current_user: CanViewJobs,
) -> list[TechnicianDirectoryItem]:
    if str(current_user.role) == UserRole.TECHNICIAN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Technician directory is for service management only",
        )

    result = await session.execute(
        select(User)
        .where(
            User.role == UserRole.TECHNICIAN.value,
            User.is_active.is_(True),
        )
        .order_by(
            User.full_name,
            User.id,
        )
    )

    return [
        TechnicianDirectoryItem(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        for user in result.scalars().all()
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
    current_user: CanViewJobs,
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
    effective_technician_id = (
        current_user.id
        if str(current_user.role)
        == "technician"
        else technician_id
    )

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
        technician_id=effective_technician_id,
        customer_id=customer_id,
        warranty_only=warranty_only,
    )


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service_job_record(
    job_id: int,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> None:
    await delete_service_job(
        session,
        job_id=job_id,
        current_user=current_user,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ServiceJobDetailResponse,
)
async def read_service_job(
    job_id: int,
    session: DatabaseSession,
    current_user: CanViewJobs,
) -> ServiceJobDetailResponse:
    job = await get_job_card(
        session,
        job_id,
    )

    ensure_technician_job_access(
        job,
        current_user,
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
    "/jobs/{job_id}/complete",
    response_model=ServiceJobDetailResponse,
)
async def complete_service_job_route(
    job_id: int,
    payload: ServiceJobCompleteRequest,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
) -> ServiceJobDetailResponse:
    job = await complete_service_job(
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
    payload: ServiceInvoiceCreateRequest | None = None,
) -> SalesInvoiceDetailResponse:
    invoice = await create_service_job_invoice(
        session=session,
        job_id=job_id,
        current_user=current_user,
        due_date=(
            payload.due_date
            if payload is not None
            else None
        ),
    )

    return await invoice_detail_response(
        session,
        invoice,
    )




# ===== LEGACY SERVICE JOB HISTORY ROUTES =====

@router.get(
    "/legacy-jobs",
)
async def read_legacy_service_jobs(
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
    cancelled: bool | None = Query(
        default=None,
    ),
):
    from app.services.service import (
        list_legacy_service_jobs,
    )

    return await list_legacy_service_jobs(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        cancelled=cancelled,
    )


@router.get(
    "/legacy-jobs/{legacy_job_id}",
)
async def read_legacy_service_job(
    legacy_job_id: int,
    session: DatabaseSession,
    _: CanViewJobs,
):
    from app.services.service import (
        get_legacy_service_job,
    )

    return await get_legacy_service_job(
        session=session,
        legacy_job_id=legacy_job_id,
    )



# ===== LEGACY SERVICE JOB STATUS ROUTE =====

@router.patch(
    "/legacy-jobs/{legacy_job_id}/status",
    response_model=LegacyServiceJobStatusUpdateResponse,
)
async def change_legacy_service_job_status(
    legacy_job_id: int,
    payload: LegacyServiceJobStatusUpdateRequest,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
):
    from app.services.service import (
        update_legacy_service_job_status,
    )

    return await update_legacy_service_job_status(
        session=session,
        legacy_job_id=legacy_job_id,
        status=payload.status,
        remarks=payload.remarks,
        user_id=current_user.id,
    )


# ===== TECHNICIAN COMPLETION EVIDENCE =====

from fastapi import File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete as sql_delete

from app.models.service_completion_evidence import (
    ServiceCompletionEvidence,
)


_COMPLETION_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

_MAX_COMPLETION_IMAGE_BYTES = 1_500_000


async def _validated_completion_image(
    upload: UploadFile,
) -> tuple[bytes, str]:
    content_type = (
        upload.content_type or ""
    ).lower()

    if content_type not in _COMPLETION_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Only JPEG, PNG or WebP images are allowed"
            ),
        )

    content = await upload.read(
        _MAX_COMPLETION_IMAGE_BYTES + 1
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image cannot be empty",
        )

    if len(content) > _MAX_COMPLETION_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Each completion image must be "
                "1.5 MB or smaller"
            ),
        )

    return content, content_type


@router.post(
    "/jobs/{job_id}/completion-evidence",
    status_code=status.HTTP_201_CREATED,
)
async def upload_service_completion_evidence(
    job_id: int,
    session: DatabaseSession,
    current_user: CanUpdateJobs,
    photos: list[UploadFile] = File(...),
    signature: UploadFile = File(...),
    customer_name: str | None = Form(default=None),
) -> dict[str, object]:
    job = await get_job_card(
        session,
        job_id,
    )

    ensure_technician_job_access(
        job,
        current_user,
    )

    if str(current_user.role) != UserRole.TECHNICIAN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Completion evidence upload is "
                "for assigned technicians only"
            ),
        )

    if len(photos) < 1 or len(photos) > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Upload between 1 and 5 work photos"
            ),
        )

    validated_photos: list[
        tuple[bytes, str, str | None]
    ] = []

    for photo in photos:
        content, content_type = (
            await _validated_completion_image(photo)
        )

        validated_photos.append(
            (
                content,
                content_type,
                photo.filename,
            )
        )

    signature_content, signature_type = (
        await _validated_completion_image(
            signature
        )
    )

    await session.execute(
        sql_delete(
            ServiceCompletionEvidence
        ).where(
            ServiceCompletionEvidence.job_card_id
            == job.id,
            ServiceCompletionEvidence.uploaded_by_id
            == current_user.id,
        )
    )

    for index, (
        content,
        content_type,
        file_name,
    ) in enumerate(
        validated_photos,
        start=1,
    ):
        session.add(
            ServiceCompletionEvidence(
                job_card_id=job.id,
                evidence_type="work_photo",
                sequence_number=index,
                content_type=content_type,
                file_name=file_name,
                content=content,
                uploaded_by_id=current_user.id,
            )
        )

    signature_name = (
        customer_name.strip()
        if customer_name
        and customer_name.strip()
        else "Customer signature"
    )

    session.add(
        ServiceCompletionEvidence(
            job_card_id=job.id,
            evidence_type="customer_signature",
            sequence_number=1,
            content_type=signature_type,
            file_name=signature_name,
            content=signature_content,
            uploaded_by_id=current_user.id,
        )
    )

    await session.commit()

    return {
        "job_id": job.id,
        "photo_count": len(
            validated_photos
        ),
        "signature_saved": True,
    }


@router.get(
    "/jobs/{job_id}/completion-evidence",
)
async def read_service_completion_evidence(
    job_id: int,
    session: DatabaseSession,
    current_user: CanViewJobs,
) -> dict[str, object]:
    job = await get_job_card(
        session,
        job_id,
    )

    ensure_technician_job_access(
        job,
        current_user,
    )

    result = await session.execute(
        select(
            ServiceCompletionEvidence
        )
        .where(
            ServiceCompletionEvidence.job_card_id
            == job.id
        )
        .order_by(
            ServiceCompletionEvidence.evidence_type,
            ServiceCompletionEvidence.sequence_number,
        )
    )

    rows = list(
        result.scalars().all()
    )

    return {
        "job_id": job.id,
        "items": [
            {
                "id": row.id,
                "evidence_type":
                    row.evidence_type,
                "sequence_number":
                    row.sequence_number,
                "content_type":
                    row.content_type,
                "file_name":
                    row.file_name,
                "created_at":
                    row.created_at,
            }
            for row in rows
        ],
    }


@router.get(
    "/jobs/{job_id}/completion-evidence/{evidence_id}/content",
)
async def read_service_completion_evidence_content(
    job_id: int,
    evidence_id: int,
    session: DatabaseSession,
    current_user: CanViewJobs,
) -> Response:
    job = await get_job_card(
        session,
        job_id,
    )

    ensure_technician_job_access(
        job,
        current_user,
    )

    result = await session.execute(
        select(
            ServiceCompletionEvidence
        ).where(
            ServiceCompletionEvidence.id
            == evidence_id,
            ServiceCompletionEvidence.job_card_id
            == job.id,
        )
    )

    evidence = (
        result.scalar_one_or_none()
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Completion evidence not found",
        )

    return Response(
        content=evidence.content,
        media_type=evidence.content_type,
        headers={
            "Cache-Control":
                "private, max-age=300",
        },
    )
