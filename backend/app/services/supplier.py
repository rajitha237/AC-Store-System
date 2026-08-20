from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Supplier, User
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.audit import create_audit_log



def supplier_audit_snapshot(
    supplier: Supplier,
) -> dict:
    return {
        "id": supplier.id,
        "supplier_code": supplier.supplier_code,
        "company_id": supplier.company_id,
        "company_name": supplier.company_name,
        "contact_person": supplier.contact_person,
        "phone": supplier.phone,
        "secondary_phone": supplier.secondary_phone,
        "email": supplier.email,
        "address_line_1": supplier.address_line_1,
        "address_line_2": supplier.address_line_2,
        "city": supplier.city,
        "registration_number":
            supplier.registration_number,
        "tax_number": supplier.tax_number,
        "credit_limit": supplier.credit_limit,
        "payment_terms_days":
            supplier.payment_terms_days,
        "current_payable":
            supplier.current_payable,
        "notes": supplier.notes,
        "is_active": supplier.is_active,
        "created_by_id":
            supplier.created_by_id,
        "updated_by_id":
            supplier.updated_by_id,
    }


async def get_default_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company)
        .where(Company.is_active.is_(True))
        .order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active company record is not configured",
        )

    return company


async def validate_supplier_duplicates(
    session: AsyncSession,
    company_id: int,
    *,
    company_name: str | None,
    phone: str | None,
    email: str | None,
    exclude_supplier_id: int | None = None,
) -> None:
    conditions = []

    if company_name:
        conditions.append(
            func.lower(Supplier.company_name)
            == company_name.lower()
        )

    if phone:
        conditions.append(Supplier.phone == phone)

    if email:
        conditions.append(
            func.lower(Supplier.email) == email.lower()
        )

    if not conditions:
        return

    statement = select(Supplier).where(
        Supplier.company_id == company_id,
        or_(*conditions),
    )

    if exclude_supplier_id is not None:
        statement = statement.where(
            Supplier.id != exclude_supplier_id
        )

    result = await session.execute(statement)
    suppliers = result.scalars().all()

    for supplier in suppliers:
        if (
            company_name
            and supplier.company_name.lower()
            == company_name.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A supplier with this company name "
                    "already exists"
                ),
            )

        if phone and supplier.phone == phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A supplier with this phone number "
                    "already exists"
                ),
            )

        if (
            email
            and supplier.email
            and supplier.email.lower() == email.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A supplier with this email address "
                    "already exists"
                ),
            )


async def create_supplier(
    session: AsyncSession,
    payload: SupplierCreate,
    current_user: User,
) -> Supplier:
    company = await get_default_company(session)

    await validate_supplier_duplicates(
        session=session,
        company_id=company.id,
        company_name=payload.company_name,
        phone=payload.phone,
        email=payload.email,
    )

    supplier = Supplier(
        company_id=company.id,
        supplier_code=None,
        company_name=payload.company_name,
        contact_person=payload.contact_person,
        phone=payload.phone,
        secondary_phone=payload.secondary_phone,
        email=payload.email,
        address_line_1=payload.address_line_1,
        address_line_2=payload.address_line_2,
        city=payload.city,
        registration_number=payload.registration_number,
        tax_number=payload.tax_number,
        credit_limit=payload.credit_limit,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
        is_active=True,
        created_by_id=current_user.id,
    )

    session.add(supplier)

    try:
        await session.flush()

        supplier.supplier_code = (
            f"SUP-{supplier.id:06d}"
        )

        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action="suppliers.supplier_created",
            module="suppliers",
            entity_type="supplier",
            entity_id=supplier.id,
            entity_reference=supplier.supplier_code,
            description="Supplier created",
            before_data=None,
            after_data=supplier_audit_snapshot(
                supplier
            ),
        )

        await session.commit()
        await session.refresh(supplier)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Supplier could not be created because "
                "a unique value already exists"
            ),
        ) from exc

    return supplier


async def list_suppliers(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    is_active: bool | None,
) -> SupplierListResponse:
    filters = []

    if search:
        normalized_search = search.strip()

        if normalized_search:
            pattern = f"%{normalized_search}%"

            filters.append(
                or_(
                    Supplier.supplier_code.ilike(pattern),
                    Supplier.company_name.ilike(pattern),
                    Supplier.contact_person.ilike(pattern),
                    Supplier.phone.ilike(pattern),
                    Supplier.email.ilike(pattern),
                    Supplier.city.ilike(pattern),
                    Supplier.registration_number.ilike(
                        pattern
                    ),
                )
            )

    if is_active is not None:
        filters.append(
            Supplier.is_active.is_(is_active)
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(Supplier)
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(Supplier)
        .where(*filters)
        .order_by(
            Supplier.company_name,
            Supplier.id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    suppliers = result.scalars().all()

    return SupplierListResponse(
        items=[
            SupplierResponse.model_validate(supplier)
            for supplier in suppliers
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


async def get_supplier_or_404(
    session: AsyncSession,
    supplier_id: int,
) -> Supplier:
    supplier = await session.get(
        Supplier,
        supplier_id,
    )

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier record was not found",
        )

    return supplier


async def update_supplier(
    session: AsyncSession,
    supplier: Supplier,
    payload: SupplierUpdate,
    current_user: User,
) -> Supplier:
    update_data = payload.model_dump(
        exclude_unset=True
    )

    before = supplier_audit_snapshot(
        supplier
    )

    company_name = update_data.get(
        "company_name",
        supplier.company_name,
    )
    phone = update_data.get(
        "phone",
        supplier.phone,
    )
    email = update_data.get(
        "email",
        supplier.email,
    )

    await validate_supplier_duplicates(
        session=session,
        company_id=supplier.company_id,
        company_name=company_name,
        phone=phone,
        email=email,
        exclude_supplier_id=supplier.id,
    )

    for field_name, value in update_data.items():
        setattr(supplier, field_name, value)

    supplier.updated_by_id = current_user.id

    after = supplier_audit_snapshot(
        supplier
    )

    before_active = before["is_active"]
    after_active = after["is_active"]

    if before_active is True and after_active is False:
        audit_action = "suppliers.supplier_deactivated"
        audit_description = "Supplier deactivated"
    elif before_active is False and after_active is True:
        audit_action = "suppliers.supplier_activated"
        audit_description = "Supplier activated"
    else:
        audit_action = "suppliers.supplier_updated"
        audit_description = "Supplier updated"

    try:
        await session.flush()

        await create_audit_log(
            session=session,
            user_id=current_user.id,
            action=audit_action,
            module="suppliers",
            entity_type="supplier",
            entity_id=supplier.id,
            entity_reference=supplier.supplier_code,
            description=audit_description,
            before_data=before,
            after_data=after,
        )

        await session.commit()
        await session.refresh(supplier)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Supplier could not be updated because "
                "a unique value already exists"
            ),
        ) from exc

    return supplier
