from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DatabaseSession, SuperUser
from app.models import Branch, Company
from app.schemas.company import (
    BranchResponse,
    BranchUpdate,
    CompanyResponse,
    CompanyUpdate,
)

router = APIRouter(
    prefix="/company",
    tags=["Company"],
)


@router.get(
    "",
    response_model=CompanyResponse,
)
async def read_company(
    session: DatabaseSession,
    _: SuperUser,
) -> CompanyResponse:
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.branches))
        .order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company record was not found",
        )

    return CompanyResponse.model_validate(company)


@router.patch(
    "",
    response_model=CompanyResponse,
)
async def update_company(
    payload: CompanyUpdate,
    session: DatabaseSession,
    _: SuperUser,
) -> CompanyResponse:
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.branches))
        .order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company record was not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        if isinstance(value, str):
            value = value.strip() or None

        setattr(company, field_name, value)

    await session.commit()

    result = await session.execute(
        select(Company)
        .options(selectinload(Company.branches))
        .where(Company.id == company.id)
    )
    updated_company = result.scalar_one()

    return CompanyResponse.model_validate(updated_company)


@router.get(
    "/branches",
    response_model=list[BranchResponse],
)
async def list_branches(
    session: DatabaseSession,
    _: SuperUser,
) -> list[BranchResponse]:
    result = await session.execute(
        select(Branch).order_by(
            Branch.is_main_branch.desc(),
            Branch.name,
        )
    )

    return [
        BranchResponse.model_validate(branch)
        for branch in result.scalars().all()
    ]


@router.patch(
    "/branches/{branch_id}",
    response_model=BranchResponse,
)
async def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    session: DatabaseSession,
    _: SuperUser,
) -> BranchResponse:
    branch = await session.get(Branch, branch_id)

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch record was not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        if isinstance(value, str):
            value = value.strip() or None

        setattr(branch, field_name, value)

    if branch.is_main_branch:
        branch.is_active = True

    await session.commit()
    await session.refresh(branch)

    return BranchResponse.model_validate(branch)
