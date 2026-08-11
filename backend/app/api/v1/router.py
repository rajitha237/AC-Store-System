from fastapi import APIRouter

from app.api.v1.access_control import (
    router as access_control_router,
)
from app.api.v1.auth import (
    router as auth_router,
)
from app.api.v1.audit import (
    router as audit_router,
)
from app.api.v1.catalog import (
    router as catalog_router,
)
from app.api.v1.company import (
    router as company_router,
)
from app.api.v1.credit_notes import (
    router as credit_notes_router,
)
from app.api.v1.customers import (
    router as customers_router,
)
from app.api.v1.documents import (
    router as documents_router,
)
from app.api.v1.health import (
    router as health_router,
)
from app.api.v1.inventory import (
    router as inventory_router,
)
from app.api.v1.payments import (
    router as payments_router,
)
from app.api.v1.sales import (
    router as sales_router,
)
from app.api.v1.returns import (
    router as returns_router,
)
from app.api.v1.service import (
    router as service_router,
)
from app.api.v1.suppliers import (
    router as suppliers_router,
)

from app.api.v1.purchasing import (
    router as purchasing_router,
)


api_router = APIRouter()

api_router.include_router(
    health_router
)

api_router.include_router(
    auth_router
)

api_router.include_router(
    audit_router
)

api_router.include_router(
    company_router
)

api_router.include_router(
    access_control_router
)

api_router.include_router(
    customers_router
)

api_router.include_router(
    suppliers_router
)

api_router.include_router(
    catalog_router
)

api_router.include_router(
    inventory_router
)

api_router.include_router(
    sales_router
)

api_router.include_router(
    returns_router
)

api_router.include_router(
    credit_notes_router
)

api_router.include_router(
    payments_router
)

api_router.include_router(
    service_router
)

api_router.include_router(
    documents_router
)

api_router.include_router(
    purchasing_router
)

