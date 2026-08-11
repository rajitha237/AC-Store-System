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
from app.models.returns import (
    ReturnResolution,
    ReturnStatus,
    ReturnType,
)
from app.schemas.returns import (
    ReplacementItemRequest,
    ReturnApprovalRequest,
    ReturnInspectionRequest,
    ReturnStatusChangeRequest,
    SalesReturnCreate,
    SalesReturnDetailResponse,
    SalesReturnListResponse,
)
from app.services.returns import (
    approve_return,
    build_return_detail,
    change_return_status,
    create_return,
    get_return,
    inspect_return,
    list_returns,
    process_return,
    set_replacement_item,
)


router = APIRouter(
    prefix="/returns",
    tags=["Returns"],
)


CanViewReturns = Annotated[
    User,
    Depends(
        require_permission("returns.view")
    ),
]


CanCreateReturns = Annotated[
    User,
    Depends(
        require_permission("returns.create")
    ),
]


CanApproveReturns = Annotated[
    User,
    Depends(
        require_permission("returns.approve")
    ),
]


@router.post(
    "",
    response_model=SalesReturnDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sales_return(
    payload: SalesReturnCreate,
    session: DatabaseSession,
    current_user: CanCreateReturns,
) -> SalesReturnDetailResponse:
    sales_return = await create_return(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.get(
    "",
    response_model=SalesReturnListResponse,
)
async def read_returns(
    session: DatabaseSession,
    _: CanViewReturns,
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
    return_status: ReturnStatus | None = None,
    return_type: ReturnType | None = None,
    resolution: ReturnResolution | None = None,
) -> SalesReturnListResponse:
    return await list_returns(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        return_status=(
            return_status.value
            if return_status is not None
            else None
        ),
        return_type=(
            return_type.value
            if return_type is not None
            else None
        ),
        resolution=(
            resolution.value
            if resolution is not None
            else None
        ),
    )


@router.get(
    "/{return_id}",
    response_model=SalesReturnDetailResponse,
)
async def read_return(
    return_id: int,
    session: DatabaseSession,
    _: CanViewReturns,
) -> SalesReturnDetailResponse:
    sales_return = await get_return(
        session,
        return_id,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.post(
    "/{return_id}/inspect",
    response_model=SalesReturnDetailResponse,
)
async def inspect_sales_return(
    return_id: int,
    payload: ReturnInspectionRequest,
    session: DatabaseSession,
    current_user: CanCreateReturns,
) -> SalesReturnDetailResponse:
    sales_return = await inspect_return(
        session=session,
        return_id=return_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.post(
    "/{return_id}/approval",
    response_model=SalesReturnDetailResponse,
)
async def approve_or_reject_return(
    return_id: int,
    payload: ReturnApprovalRequest,
    session: DatabaseSession,
    current_user: CanApproveReturns,
) -> SalesReturnDetailResponse:
    sales_return = await approve_return(
        session=session,
        return_id=return_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.post(
    "/{return_id}/process",
    response_model=SalesReturnDetailResponse,
)
async def process_sales_return(
    return_id: int,
    session: DatabaseSession,
    current_user: CanApproveReturns,
) -> SalesReturnDetailResponse:
    sales_return = await process_return(
        session=session,
        return_id=return_id,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.post(
    "/{return_id}/replacement",
    response_model=SalesReturnDetailResponse,
)
async def issue_return_replacement(
    return_id: int,
    payload: ReplacementItemRequest,
    session: DatabaseSession,
    current_user: CanApproveReturns,
) -> SalesReturnDetailResponse:
    sales_return = await set_replacement_item(
        session=session,
        return_id=return_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )


@router.post(
    "/{return_id}/status",
    response_model=SalesReturnDetailResponse,
)
async def update_return_status(
    return_id: int,
    payload: ReturnStatusChangeRequest,
    session: DatabaseSession,
    current_user: CanApproveReturns,
) -> SalesReturnDetailResponse:
    sales_return = await change_return_status(
        session=session,
        return_id=return_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_return_detail(
        session,
        sales_return,
    )
