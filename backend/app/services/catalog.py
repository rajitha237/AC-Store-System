from __future__ import annotations

from math import ceil
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Brand,
    Company,
    Product,
    ProductCategory,
    StockItem,
    UnitOfMeasure,
    User,
)
from app.schemas.catalog import (
    BrandCreate,
    BrandUpdate,
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)


async def get_active_company(
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


async def get_category_or_404(
    session: AsyncSession,
    category_id: int,
) -> ProductCategory:
    category = await session.get(
        ProductCategory,
        category_id,
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category was not found",
        )

    return category


async def create_category(
    session: AsyncSession,
    payload: CategoryCreate,
) -> ProductCategory:
    company = await get_active_company(session)

    if payload.parent_id is not None:
        parent = await get_category_or_404(
            session,
            payload.parent_id,
        )

        if parent.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Parent category belongs to another company",
            )

    category = ProductCategory(
        company_id=company.id,
        parent_id=payload.parent_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=True,
    )

    session.add(category)

    try:
        await session.commit()
        await session.refresh(category)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A category with this code or name "
                "already exists"
            ),
        ) from exc

    return category


async def list_categories(
    session: AsyncSession,
    *,
    search: str | None,
    is_active: bool | None,
) -> list[ProductCategory]:
    filters = []

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                ProductCategory.code.ilike(pattern),
                ProductCategory.name.ilike(pattern),
                ProductCategory.description.ilike(pattern),
            )
        )

    if is_active is not None:
        filters.append(
            ProductCategory.is_active.is_(is_active)
        )

    result = await session.execute(
        select(ProductCategory)
        .where(*filters)
        .order_by(
            ProductCategory.name,
            ProductCategory.id,
        )
    )

    return list(result.scalars().all())


async def update_category(
    session: AsyncSession,
    category: ProductCategory,
    payload: CategoryUpdate,
) -> ProductCategory:
    update_data = payload.model_dump(exclude_unset=True)

    if "parent_id" in update_data:
        parent_id = update_data["parent_id"]

        if parent_id == category.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category cannot be its own parent",
            )

        if parent_id is not None:
            parent = await get_category_or_404(
                session,
                parent_id,
            )

            if parent.company_id != category.company_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Parent category belongs to "
                        "another company"
                    ),
                )

    for field_name, value in update_data.items():
        setattr(category, field_name, value)

    try:
        await session.commit()
        await session.refresh(category)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Category could not be updated because "
                "the code or name already exists"
            ),
        ) from exc

    return category


async def get_brand_or_404(
    session: AsyncSession,
    brand_id: int,
) -> Brand:
    brand = await session.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand was not found",
        )

    return brand


async def create_brand(
    session: AsyncSession,
    payload: BrandCreate,
) -> Brand:
    company = await get_active_company(session)

    brand = Brand(
        company_id=company.id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=True,
    )

    session.add(brand)

    try:
        await session.commit()
        await session.refresh(brand)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A brand with this code or name "
                "already exists"
            ),
        ) from exc

    return brand


async def list_brands(
    session: AsyncSession,
    *,
    search: str | None,
    is_active: bool | None,
) -> list[Brand]:
    filters = []

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                Brand.code.ilike(pattern),
                Brand.name.ilike(pattern),
                Brand.description.ilike(pattern),
            )
        )

    if is_active is not None:
        filters.append(Brand.is_active.is_(is_active))

    result = await session.execute(
        select(Brand)
        .where(*filters)
        .order_by(Brand.name, Brand.id)
    )

    return list(result.scalars().all())


async def update_brand(
    session: AsyncSession,
    brand: Brand,
    payload: BrandUpdate,
) -> Brand:
    update_data = payload.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(brand, field_name, value)

    try:
        await session.commit()
        await session.refresh(brand)
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Brand could not be updated because "
                "the code or name already exists"
            ),
        ) from exc

    return brand


async def get_unit_or_404(
    session: AsyncSession,
    unit_id: int,
) -> UnitOfMeasure:
    unit = await session.get(UnitOfMeasure, unit_id)

    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit of measure was not found",
        )

    if not unit.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unit of measure is inactive",
        )

    return unit


async def validate_product_references(
    session: AsyncSession,
    *,
    company_id: int,
    category_id: int,
    brand_id: int | None,
    unit_id: int,
) -> None:
    category = await get_category_or_404(
        session,
        category_id,
    )

    if category.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category belongs to another company",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected category is inactive",
        )

    if brand_id is not None:
        brand = await get_brand_or_404(
            session,
            brand_id,
        )

        if brand.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Brand belongs to another company",
            )

        if not brand.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected brand is inactive",
            )

    await get_unit_or_404(session, unit_id)


async def get_product_or_404(
    session: AsyncSession,
    product_id: int,
) -> Product:
    result = await session.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.unit),
        )
        .where(Product.id == product_id)
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product was not found",
        )

    return product


async def create_product(
    session: AsyncSession,
    payload: ProductCreate,
    current_user: User,
) -> Product:
    company = await get_active_company(session)

    await validate_product_references(
        session=session,
        company_id=company.id,
        category_id=payload.category_id,
        brand_id=payload.brand_id,
        unit_id=payload.unit_id,
    )

    temporary_code = (
        f"TMP-{uuid4().hex.upper()[:20]}"
    )

    product = Product(
        company_id=company.id,
        product_code=temporary_code,
        barcode=payload.barcode,
        category_id=payload.category_id,
        brand_id=payload.brand_id,
        unit_id=payload.unit_id,
        name=payload.name,
        model_number=payload.model_number,
        description=payload.description,
        btu_capacity=payload.btu_capacity,
        product_type=payload.product_type.value,
        track_serial_numbers=payload.track_serial_numbers,
        purchase_cost=payload.purchase_cost,
        selling_price=payload.selling_price,
        minimum_selling_price=(
            payload.minimum_selling_price
        ),
        warranty_months=payload.warranty_months,
        reorder_level=payload.reorder_level,
        reorder_quantity=payload.reorder_quantity,
        image_path=payload.image_path,
        technical_notes=payload.technical_notes,
        is_active=True,
        created_by_id=current_user.id,
    )

    session.add(product)

    try:
        await session.flush()

        product.product_code = (
            f"PRD-{product.id:06d}"
        )

        await session.commit()
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Product could not be created. "
                "The barcode or another unique value "
                "already exists"
            ),
        ) from exc

    return await get_product_or_404(
        session,
        product.id,
    )


async def list_products(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    search: str | None,
    category_id: int | None,
    brand_id: int | None,
    product_type: str | None,
    track_serial_numbers: bool | None,
    is_active: bool | None,
) -> ProductListResponse:
    filters = []

    if search and search.strip():
        pattern = f"%{search.strip()}%"

        filters.append(
            or_(
                Product.product_code.ilike(pattern),
                Product.barcode.ilike(pattern),
                Product.name.ilike(pattern),
                Product.model_number.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if brand_id is not None:
        filters.append(Product.brand_id == brand_id)

    if product_type is not None:
        filters.append(
            Product.product_type == product_type
        )

    if track_serial_numbers is not None:
        filters.append(
            Product.track_serial_numbers.is_(
                track_serial_numbers
            )
        )

    if is_active is not None:
        filters.append(Product.is_active.is_(is_active))

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(Product)
            .where(*filters)
        )
        or 0
    )

    result = await session.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.unit),
        )
        .where(*filters)
        .order_by(Product.name, Product.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    products = result.scalars().all()

    return ProductListResponse(
        items=[
            ProductResponse.model_validate(product)
            for product in products
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
    )


async def update_product(
    session: AsyncSession,
    product: Product,
    payload: ProductUpdate,
    current_user: User,
) -> Product:
    update_data = payload.model_dump(exclude_unset=True)

    category_id = update_data.get(
        "category_id",
        product.category_id,
    )
    brand_id = update_data.get(
        "brand_id",
        product.brand_id,
    )
    unit_id = update_data.get(
        "unit_id",
        product.unit_id,
    )

    await validate_product_references(
        session=session,
        company_id=product.company_id,
        category_id=category_id,
        brand_id=brand_id,
        unit_id=unit_id,
    )

    selling_price = update_data.get(
        "selling_price",
        product.selling_price,
    )
    minimum_price = update_data.get(
        "minimum_selling_price",
        product.minimum_selling_price,
    )

    if minimum_price > selling_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Minimum selling price cannot be greater "
                "than selling price"
            ),
        )

    if (
        "track_serial_numbers" in update_data
        and update_data["track_serial_numbers"]
        != product.track_serial_numbers
    ):
        stock_count = int(
            await session.scalar(
                select(func.count())
                .select_from(StockItem)
                .where(StockItem.product_id == product.id)
            )
            or 0
        )

        if stock_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Serial tracking cannot be changed "
                    "after stock records exist"
                ),
            )

    for field_name, value in update_data.items():
        if hasattr(value, "value"):
            value = value.value

        setattr(product, field_name, value)

    product.updated_by_id = current_user.id

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Product could not be updated. "
                "The barcode or another unique value "
                "already exists"
            ),
        ) from exc

    return await get_product_or_404(
        session,
        product.id,
    )
