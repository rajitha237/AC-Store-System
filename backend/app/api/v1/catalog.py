from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import UnitOfMeasure, User
from app.schemas.catalog import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductType,
    ProductUpdate,
    UnitResponse,
)
from app.services.catalog import (
    create_brand,
    create_category,
    create_product,
    get_brand_or_404,
    get_category_or_404,
    get_product_or_404,
    list_brands,
    list_categories,
    list_products,
    update_brand,
    update_category,
    update_product,
)

router = APIRouter(
    prefix="/catalog",
    tags=["Product Catalog"],
)

CanViewProducts = Annotated[
    User,
    Depends(require_permission("products.view")),
]

CanManageProducts = Annotated[
    User,
    Depends(require_permission("products.manage")),
]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
)
async def read_categories(
    session: DatabaseSession,
    _: CanViewProducts,
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    is_active: bool | None = None,
) -> list[CategoryResponse]:
    categories = await list_categories(
        session=session,
        search=search,
        is_active=is_active,
    )

    return [
        CategoryResponse.model_validate(category)
        for category in categories
    ]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_record(
    payload: CategoryCreate,
    session: DatabaseSession,
    _: CanManageProducts,
) -> CategoryResponse:
    category = await create_category(
        session=session,
        payload=payload,
    )

    return CategoryResponse.model_validate(category)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def update_category_record(
    category_id: int,
    payload: CategoryUpdate,
    session: DatabaseSession,
    _: CanManageProducts,
) -> CategoryResponse:
    category = await get_category_or_404(
        session,
        category_id,
    )

    updated = await update_category(
        session=session,
        category=category,
        payload=payload,
    )

    return CategoryResponse.model_validate(updated)


@router.delete(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def deactivate_category(
    category_id: int,
    session: DatabaseSession,
    _: CanManageProducts,
) -> CategoryResponse:
    category = await get_category_or_404(
        session,
        category_id,
    )

    updated = await update_category(
        session=session,
        category=category,
        payload=CategoryUpdate(is_active=False),
    )

    return CategoryResponse.model_validate(updated)


@router.get(
    "/brands",
    response_model=list[BrandResponse],
)
async def read_brands(
    session: DatabaseSession,
    _: CanViewProducts,
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    is_active: bool | None = None,
) -> list[BrandResponse]:
    brands = await list_brands(
        session=session,
        search=search,
        is_active=is_active,
    )

    return [
        BrandResponse.model_validate(brand)
        for brand in brands
    ]


@router.post(
    "/brands",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_record(
    payload: BrandCreate,
    session: DatabaseSession,
    _: CanManageProducts,
) -> BrandResponse:
    brand = await create_brand(
        session=session,
        payload=payload,
    )

    return BrandResponse.model_validate(brand)


@router.patch(
    "/brands/{brand_id}",
    response_model=BrandResponse,
)
async def update_brand_record(
    brand_id: int,
    payload: BrandUpdate,
    session: DatabaseSession,
    _: CanManageProducts,
) -> BrandResponse:
    brand = await get_brand_or_404(
        session,
        brand_id,
    )

    updated = await update_brand(
        session=session,
        brand=brand,
        payload=payload,
    )

    return BrandResponse.model_validate(updated)


@router.delete(
    "/brands/{brand_id}",
    response_model=BrandResponse,
)
async def deactivate_brand(
    brand_id: int,
    session: DatabaseSession,
    _: CanManageProducts,
) -> BrandResponse:
    brand = await get_brand_or_404(
        session,
        brand_id,
    )

    updated = await update_brand(
        session=session,
        brand=brand,
        payload=BrandUpdate(is_active=False),
    )

    return BrandResponse.model_validate(updated)


@router.get(
    "/units",
    response_model=list[UnitResponse],
)
async def read_units(
    session: DatabaseSession,
    _: CanViewProducts,
) -> list[UnitResponse]:
    result = await session.execute(
        select(UnitOfMeasure)
        .where(UnitOfMeasure.is_active.is_(True))
        .order_by(UnitOfMeasure.name)
    )

    return [
        UnitResponse.model_validate(unit)
        for unit in result.scalars().all()
    ]


@router.get(
    "/products",
    response_model=ProductListResponse,
)
async def read_products(
    session: DatabaseSession,
    _: CanViewProducts,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    category_id: int | None = Query(
        default=None,
        ge=1,
    ),
    brand_id: int | None = Query(
        default=None,
        ge=1,
    ),
    product_type: ProductType | None = None,
    track_serial_numbers: bool | None = None,
    is_active: bool | None = None,
) -> ProductListResponse:
    return await list_products(
        session=session,
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
        product_type=(
            product_type.value
            if product_type is not None
            else None
        ),
        track_serial_numbers=track_serial_numbers,
        is_active=is_active,
    )


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_record(
    payload: ProductCreate,
    session: DatabaseSession,
    current_user: CanManageProducts,
) -> ProductResponse:
    product = await create_product(
        session=session,
        payload=payload,
        current_user=current_user,
    )

    return ProductResponse.model_validate(product)


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
)
async def read_product(
    product_id: int,
    session: DatabaseSession,
    _: CanViewProducts,
) -> ProductResponse:
    product = await get_product_or_404(
        session,
        product_id,
    )

    return ProductResponse.model_validate(product)


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
)
async def update_product_record(
    product_id: int,
    payload: ProductUpdate,
    session: DatabaseSession,
    current_user: CanManageProducts,
) -> ProductResponse:
    product = await get_product_or_404(
        session,
        product_id,
    )

    updated = await update_product(
        session=session,
        product=product,
        payload=payload,
        current_user=current_user,
    )

    return ProductResponse.model_validate(updated)


@router.delete(
    "/products/{product_id}",
    response_model=ProductResponse,
)
async def deactivate_product(
    product_id: int,
    session: DatabaseSession,
    current_user: CanManageProducts,
) -> ProductResponse:
    product = await get_product_or_404(
        session,
        product_id,
    )

    updated = await update_product(
        session=session,
        product=product,
        payload=ProductUpdate(is_active=False),
        current_user=current_user,
    )

    return ProductResponse.model_validate(updated)
