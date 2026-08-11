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
from app.models.credit_note import (
    CreditNoteStatus,
)
from app.schemas.credit_note import (
    CreditNoteApprovalRequest,
    CreditNoteCreate,
    CreditNoteDetailResponse,
    CustomerRefundResponse,
    FinancialReversalRequest,
    RefundCreate,
)
from app.services.credit_note import (
    approve_credit_note,
    build_credit_note_detail,
    create_credit_note,
    create_refund,
    get_credit_note,
    list_credit_notes,
    post_credit_note,
    post_refund,
    reverse_credit_note,
    reverse_refund,
)


router = APIRouter(
    prefix="/credit-notes",
    tags=["Credit Notes & Refunds"],
)


CanViewCreditNotes = Annotated[
    User,
    Depends(
        require_permission("credit_notes.view")
    ),
]

CanCreateCreditNotes = Annotated[
    User,
    Depends(
        require_permission("credit_notes.create")
    ),
]

CanApproveCreditNotes = Annotated[
    User,
    Depends(
        require_permission("credit_notes.approve")
    ),
]

CanPostCreditNotes = Annotated[
    User,
    Depends(
        require_permission("credit_notes.post")
    ),
]

CanReverseCreditNotes = Annotated[
    User,
    Depends(
        require_permission("credit_notes.reverse")
    ),
]

CanCreateRefunds = Annotated[
    User,
    Depends(
        require_permission("refunds.create")
    ),
]

CanPostRefunds = Annotated[
    User,
    Depends(
        require_permission("refunds.post")
    ),
]

CanReverseRefunds = Annotated[
    User,
    Depends(
        require_permission("refunds.reverse")
    ),
]


@router.post(
    "",
    response_model=CreditNoteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_credit_note_api(
    payload: CreditNoteCreate,
    session: DatabaseSession,
    current_user: CanCreateCreditNotes,
) -> CreditNoteDetailResponse:
    credit_note = await create_credit_note(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return await build_credit_note_detail(
        session,
        credit_note,
    )


@router.get(
    "",
)
async def read_credit_notes(
    session: DatabaseSession,
    _: CanViewCreditNotes,
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
    credit_note_status: CreditNoteStatus | None = None,
):
    return await list_credit_notes(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        credit_note_status=(
            credit_note_status.value
            if credit_note_status is not None
            else None
        ),
    )


@router.get(
    "/{credit_note_id}",
    response_model=CreditNoteDetailResponse,
)
async def read_credit_note(
    credit_note_id: int,
    session: DatabaseSession,
    _: CanViewCreditNotes,
) -> CreditNoteDetailResponse:
    credit_note = await get_credit_note(
        session,
        credit_note_id,
    )

    return await build_credit_note_detail(
        session,
        credit_note,
    )


@router.post(
    "/{credit_note_id}/approval",
    response_model=CreditNoteDetailResponse,
)
async def approve_credit_note_api(
    credit_note_id: int,
    payload: CreditNoteApprovalRequest,
    session: DatabaseSession,
    current_user: CanApproveCreditNotes,
) -> CreditNoteDetailResponse:
    credit_note = await approve_credit_note(
        session=session,
        credit_note_id=credit_note_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_credit_note_detail(
        session,
        credit_note,
    )


@router.post(
    "/{credit_note_id}/post",
    response_model=CreditNoteDetailResponse,
)
async def post_credit_note_api(
    credit_note_id: int,
    session: DatabaseSession,
    current_user: CanPostCreditNotes,
) -> CreditNoteDetailResponse:
    credit_note = await post_credit_note(
        session=session,
        credit_note_id=credit_note_id,
        current_user=current_user,
    )

    return await build_credit_note_detail(
        session,
        credit_note,
    )


@router.post(
    "/{credit_note_id}/reverse",
    response_model=CreditNoteDetailResponse,
)
async def reverse_credit_note_api(
    credit_note_id: int,
    payload: FinancialReversalRequest,
    session: DatabaseSession,
    current_user: CanReverseCreditNotes,
) -> CreditNoteDetailResponse:
    credit_note = await reverse_credit_note(
        session=session,
        credit_note_id=credit_note_id,
        payload=payload,
        current_user=current_user,
    )

    return await build_credit_note_detail(
        session,
        credit_note,
    )


@router.post(
    "/refunds",
    response_model=CustomerRefundResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_refund_api(
    payload: RefundCreate,
    session: DatabaseSession,
    current_user: CanCreateRefunds,
) -> CustomerRefundResponse:
    refund = await create_refund(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return CustomerRefundResponse.model_validate(
        refund
    )


@router.post(
    "/refunds/{refund_id}/post",
    response_model=CustomerRefundResponse,
)
async def post_refund_api(
    refund_id: int,
    session: DatabaseSession,
    current_user: CanPostRefunds,
) -> CustomerRefundResponse:
    refund = await post_refund(
        session=session,
        refund_id=refund_id,
        current_user=current_user,
    )

    return CustomerRefundResponse.model_validate(
        refund
    )


@router.post(
    "/refunds/{refund_id}/reverse",
    response_model=CustomerRefundResponse,
)
async def reverse_refund_api(
    refund_id: int,
    payload: FinancialReversalRequest,
    session: DatabaseSession,
    current_user: CanReverseRefunds,
) -> CustomerRefundResponse:
    refund = await reverse_refund(
        session=session,
        refund_id=refund_id,
        payload=payload,
        current_user=current_user,
    )

    return CustomerRefundResponse.model_validate(
        refund
    )
