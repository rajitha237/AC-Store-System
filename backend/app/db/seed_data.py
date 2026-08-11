from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Branch, Company, Permission, Role, RolePermission


@dataclass(frozen=True)
class RoleSeed:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class PermissionSeed:
    code: str
    module: str
    name: str
    description: str


SYSTEM_ROLES: tuple[RoleSeed, ...] = (
    RoleSeed(
        code="super_admin",
        name="Super Administrator",
        description="Full system access and system configuration control.",
    ),
    RoleSeed(
        code="owner",
        name="Owner",
        description="Business owner access to operations, finance and reports.",
    ),
    RoleSeed(
        code="manager",
        name="Manager",
        description="Manages daily operations and approval workflows.",
    ),
    RoleSeed(
        code="accountant",
        name="Accountant",
        description="Manages accounting, expenses, payments and reports.",
    ),
    RoleSeed(
        code="sales_officer",
        name="Sales Officer",
        description="Manages customers, quotations, sales and installments.",
    ),
    RoleSeed(
        code="cashier",
        name="Cashier",
        description="Receives customer payments and operates the cash drawer.",
    ),
    RoleSeed(
        code="service_manager",
        name="Service Manager",
        description="Manages job cards, repairs and warranty workflows.",
    ),
    RoleSeed(
        code="technician",
        name="Technician",
        description="Updates inspections, repair notes and testing results.",
    ),
    RoleSeed(
        code="stock_keeper",
        name="Stock Keeper",
        description="Manages stock receiving, movements and stock counts.",
    ),
)


SYSTEM_PERMISSIONS: tuple[PermissionSeed, ...] = (
    PermissionSeed(
        code="dashboard.view",
        module="dashboard",
        name="View Dashboard",
        description="View operational dashboard information.",
    ),
    PermissionSeed(
        code="users.view",
        module="users",
        name="View Users",
        description="View staff user accounts.",
    ),
    PermissionSeed(
        code="users.manage",
        module="users",
        name="Manage Users",
        description="Create, update and deactivate staff users.",
    ),
    PermissionSeed(
        code="roles.view",
        module="roles",
        name="View Roles",
        description="View roles and assigned permissions.",
    ),
    PermissionSeed(
        code="roles.manage",
        module="roles",
        name="Manage Roles",
        description="Manage roles and permission assignments.",
    ),
    PermissionSeed(
        code="company.view",
        module="company",
        name="View Company",
        description="View company and branch information.",
    ),
    PermissionSeed(
        code="company.manage",
        module="company",
        name="Manage Company",
        description="Update company, branch and system settings.",
    ),
    PermissionSeed(
        code="customers.view",
        module="customers",
        name="View Customers",
        description="View customer records and customer history.",
    ),
    PermissionSeed(
        code="customers.create",
        module="customers",
        name="Create Customers",
        description="Create customer records.",
    ),
    PermissionSeed(
        code="customers.update",
        module="customers",
        name="Update Customers",
        description="Update customer details.",
    ),
    PermissionSeed(
        code="suppliers.view",
        module="suppliers",
        name="View Suppliers",
        description="View supplier records.",
    ),
    PermissionSeed(
        code="suppliers.manage",
        module="suppliers",
        name="Manage Suppliers",
        description="Create and update supplier records.",
    ),
    PermissionSeed(
        code="products.view",
        module="products",
        name="View Products",
        description="View products, prices and availability.",
    ),
    PermissionSeed(
        code="products.manage",
        module="products",
        name="Manage Products",
        description="Create and update product records.",
    ),
    PermissionSeed(
        code="inventory.view",
        module="inventory",
        name="View Inventory",
        description="View stock and serial-number information.",
    ),
    PermissionSeed(
        code="inventory.receive",
        module="inventory",
        name="Receive Inventory",
        description="Receive purchased products into stock.",
    ),
    PermissionSeed(
        code="inventory.adjust",
        module="inventory",
        name="Adjust Inventory",
        description="Create approved stock adjustments.",
    ),
    PermissionSeed(
        code="sales.view",
        module="sales",
        name="View Sales",
        description="View sales invoices and sales history.",
    ),
    PermissionSeed(
        code="sales.create",
        module="sales",
        name="Create Sales",
        description="Create and confirm sales invoices.",
    ),
    PermissionSeed(
        code="sales.approve_discount",
        module="sales",
        name="Approve Sales Discounts",
        description="Approve restricted discounts and pricing exceptions.",
    ),
    PermissionSeed(
        code="payments.view",
        module="payments",
        name="View Payments",
        description="View receipts and payment history.",
    ),
    PermissionSeed(
        code="payments.receive",
        module="payments",
        name="Receive Payments",
        description="Receive customer and installment payments.",
    ),
    PermissionSeed(
        code="payments.reverse",
        module="payments",
        name="Reverse Payments",
        description="Reverse an incorrect posted payment.",
    ),
    PermissionSeed(
        code="installments.view",
        module="installments",
        name="View Installments",
        description="View installment agreements and schedules.",
    ),
    PermissionSeed(
        code="installments.manage",
        module="installments",
        name="Manage Installments",
        description="Create and update installment agreements.",
    ),
    PermissionSeed(
        code="installments.approve",
        module="installments",
        name="Approve Installments",
        description="Approve installment agreements and changes.",
    ),
    PermissionSeed(
        code="job_cards.view",
        module="job_cards",
        name="View Job Cards",
        description="View job cards and repair progress.",
    ),
    PermissionSeed(
        code="job_cards.create",
        module="job_cards",
        name="Create Job Cards",
        description="Create service and repair job cards.",
    ),
    PermissionSeed(
        code="job_cards.update",
        module="job_cards",
        name="Update Job Cards",
        description="Update inspections, repairs and job-card status.",
    ),
    PermissionSeed(
        code="warranties.manage",
        module="warranties",
        name="Manage Warranties",
        description="Manage warranty records and warranty claims.",
    ),
    PermissionSeed(
        code="returns.view",
        module="returns",
        name="View Returns",
        description="View product return and replacement records.",
    ),
    PermissionSeed(
        code="returns.create",
        module="returns",
        name="Create Returns",
        description="Create return and replacement requests.",
    ),
    PermissionSeed(
        code="returns.approve",
        module="returns",
        name="Approve Returns",
        description="Approve returns, replacements and refunds.",
    ),
    PermissionSeed(
        code="credit_notes.view",
        module="credit_notes",
        name="View Credit Notes",
        description="View credit notes and related refund records.",
    ),
    PermissionSeed(
        code="credit_notes.create",
        module="credit_notes",
        name="Create Credit Notes",
        description="Create credit notes from approved returns.",
    ),
    PermissionSeed(
        code="credit_notes.approve",
        module="credit_notes",
        name="Approve Credit Notes",
        description="Approve draft credit notes.",
    ),
    PermissionSeed(
        code="credit_notes.post",
        module="credit_notes",
        name="Post Credit Notes",
        description="Post approved credit notes to customer accounts.",
    ),
    PermissionSeed(
        code="credit_notes.reverse",
        module="credit_notes",
        name="Reverse Credit Notes",
        description="Reverse posted credit notes with audit history.",
    ),
    PermissionSeed(
        code="refunds.create",
        module="refunds",
        name="Create Refunds",
        description="Create customer refunds from posted credit notes.",
    ),
    PermissionSeed(
        code="refunds.post",
        module="refunds",
        name="Post Refunds",
        description="Post approved customer refund transactions.",
    ),
    PermissionSeed(
        code="refunds.reverse",
        module="refunds",
        name="Reverse Refunds",
        description="Reverse posted customer refunds with audit history.",
    ),
    PermissionSeed(
        code="accounting.view",
        module="accounting",
        name="View Accounting",
        description="View accounting entries and financial reports.",
    ),
    PermissionSeed(
        code="accounting.post",
        module="accounting",
        name="Post Accounting Entries",
        description="Post journal entries and financial transactions.",
    ),
    PermissionSeed(
        code="expenses.manage",
        module="expenses",
        name="Manage Expenses",
        description="Create, approve and post business expenses.",
    ),
    PermissionSeed(
        code="reports.view",
        module="reports",
        name="View Reports",
        description="View and export operational and financial reports.",
    ),
    PermissionSeed(
        code="sms.view",
        module="sms",
        name="View SMS",
        description="View customer SMS messages and delivery status.",
    ),
    PermissionSeed(
        code="sms.manage",
        module="sms",
        name="Manage SMS",
        description="Manage SMS templates and retry failed messages.",
    ),
    PermissionSeed(
        code="ai_alerts.view",
        module="ai_alerts",
        name="View AI Alerts",
        description="View AI monitoring alerts and business warnings.",
    ),
    PermissionSeed(
        code="audit.view",
        module="audit",
        name="View Audit Logs",
        description="View sensitive system and user activity logs.",
    ),
    PermissionSeed(
        code="purchasing.view",
        module="purchasing",
        name="View Purchase Orders",
        description=(
            "View purchase orders and "
            "procurement information."
        ),
    ),
    PermissionSeed(
        code="purchasing.manage",
        module="purchasing",
        name="Manage Purchase Orders",
        description=(
            "Create and update purchase "
            "order drafts and cancellations."
        ),
    ),
    PermissionSeed(
        code="purchasing.approve",
        module="purchasing",
        name="Approve Purchase Orders",
        description=(
            "Approve purchase orders for "
            "supplier procurement."
        ),
    ),
    PermissionSeed(
        code="purchasing.receive",
        module="purchasing",
        name="Receive Purchase Orders",
        description=(
            "Post goods receipts against "
            "approved purchase orders."
        ),
    ),
    PermissionSeed(
        code="purchasing.finance",
        module="purchasing",
        name="Manage Supplier Finance",
        description=(
            "Create supplier invoices, "
            "post supplier payments, and "
            "perform reversals."
        ),
    ),

)


ROLE_PERMISSION_CODES: dict[str, set[str]] = {
    "super_admin": {
        permission.code for permission in SYSTEM_PERMISSIONS
    },
    "owner": {
        permission.code for permission in SYSTEM_PERMISSIONS
        if permission.code not in {
            "users.manage",
            "roles.manage",
        }
    },
    "manager": {
        "dashboard.view",
        "users.view",
        "company.view",
        "customers.view",
        "customers.create",
        "customers.update",
        "suppliers.view",
        "suppliers.manage",
        "products.view",
        "products.manage",
        "inventory.view",
        "inventory.receive",
        "inventory.adjust",
        "sales.view",
        "sales.create",
        "sales.approve_discount",
        "payments.view",
        "payments.receive",
        "installments.view",
        "installments.manage",
        "installments.approve",
        "job_cards.view",
        "job_cards.create",
        "job_cards.update",
        "warranties.manage",
        "returns.view",
        "returns.create",
        "returns.approve",
        "credit_notes.view",
        "credit_notes.create",
        "credit_notes.approve",
        "credit_notes.post",
        "credit_notes.reverse",
        "refunds.create",
        "refunds.post",
        "refunds.reverse",
        "accounting.view",
        "expenses.manage",
        "reports.view",
        "sms.view",
        "ai_alerts.view",
        "purchasing.view",
        "purchasing.manage",
        "purchasing.approve",

        "purchasing.receive",
        "purchasing.finance",
    },
    "accountant": {
        "dashboard.view",
        "customers.view",
        "suppliers.view",
        "products.view",
        "inventory.view",
        "sales.view",
        "payments.view",
        "payments.receive",
        "payments.reverse",
        "installments.view",
        "credit_notes.view",
        "credit_notes.post",
        "credit_notes.reverse",
        "refunds.create",
        "refunds.post",
        "refunds.reverse",
        "accounting.view",
        "accounting.post",
        "expenses.manage",
        "reports.view",
        "sms.view",
        "purchasing.view",

    },
    "sales_officer": {
        "dashboard.view",
        "customers.view",
        "customers.create",
        "customers.update",
        "products.view",
        "inventory.view",
        "sales.view",
        "sales.create",
        "payments.view",
        "installments.view",
        "installments.manage",
        "job_cards.view",
        "job_cards.create",
        "returns.view",
        "returns.create",
        "credit_notes.view",
        "credit_notes.create",
    },
    "cashier": {
        "dashboard.view",
        "customers.view",
        "products.view",
        "inventory.view",
        "sales.view",
        "payments.view",
        "payments.receive",
        "installments.view",
        "job_cards.view",
        "credit_notes.view",
        "refunds.post",
        "reports.view",
    },
    "service_manager": {
        "dashboard.view",
        "customers.view",
        "products.view",
        "inventory.view",
        "job_cards.view",
        "job_cards.create",
        "job_cards.update",
        "warranties.manage",
        "returns.view",
        "returns.create",
        "returns.approve",
        "credit_notes.view",
        "credit_notes.create",
        "credit_notes.approve",
        "credit_notes.post",
        "refunds.create",
        "payments.view",
        "payments.receive",
        "sms.view",
        "ai_alerts.view",
    },
    "technician": {
        "dashboard.view",
        "customers.view",
        "products.view",
        "inventory.view",
        "job_cards.view",
        "job_cards.update",
    },
    "stock_keeper": {
        "dashboard.view",
        "suppliers.view",
        "products.view",
        "inventory.view",
        "inventory.receive",
        "job_cards.view",
        "returns.view",
    },
}


async def seed_default_company(
    session: AsyncSession,
) -> Company:
    result = await session.execute(
        select(Company).order_by(Company.id)
    )
    company = result.scalars().first()

    if company is None:
        company = Company(
            name="AC Store",
            legal_name="AC Store",
            currency_code="LKR",
            timezone="Asia/Colombo",
            is_active=True,
        )
        session.add(company)
        await session.flush()

    return company


async def seed_main_branch(
    session: AsyncSession,
    company: Company,
) -> Branch:
    result = await session.execute(
        select(Branch).where(
            Branch.company_id == company.id,
            Branch.code == "MAIN",
        )
    )
    branch = result.scalar_one_or_none()

    if branch is None:
        branch = Branch(
            company_id=company.id,
            code="MAIN",
            name="Main Store",
            is_main_branch=True,
            is_active=True,
        )
        session.add(branch)
        await session.flush()

    return branch


async def seed_roles(
    session: AsyncSession,
) -> dict[str, Role]:
    result = await session.execute(select(Role))
    existing_roles = {
        role.code: role
        for role in result.scalars().all()
    }

    for role_seed in SYSTEM_ROLES:
        role = existing_roles.get(role_seed.code)

        if role is None:
            role = Role(
                code=role_seed.code,
                name=role_seed.name,
                description=role_seed.description,
                is_system_role=True,
                is_active=True,
            )
            session.add(role)
            await session.flush()
            existing_roles[role.code] = role
        else:
            role.name = role_seed.name
            role.description = role_seed.description
            role.is_system_role = True

    return existing_roles


async def seed_permissions(
    session: AsyncSession,
) -> dict[str, Permission]:
    result = await session.execute(select(Permission))
    existing_permissions = {
        permission.code: permission
        for permission in result.scalars().all()
    }

    for permission_seed in SYSTEM_PERMISSIONS:
        permission = existing_permissions.get(permission_seed.code)

        if permission is None:
            permission = Permission(
                code=permission_seed.code,
                module=permission_seed.module,
                name=permission_seed.name,
                description=permission_seed.description,
            )
            session.add(permission)
            await session.flush()
            existing_permissions[permission.code] = permission
        else:
            permission.module = permission_seed.module
            permission.name = permission_seed.name
            permission.description = permission_seed.description

    return existing_permissions


async def seed_role_permissions(
    session: AsyncSession,
    roles: dict[str, Role],
    permissions: dict[str, Permission],
) -> None:
    result = await session.execute(select(RolePermission))
    existing_links = {
        (link.role_id, link.permission_id)
        for link in result.scalars().all()
    }

    for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
        role = roles[role_code]

        for permission_code in permission_codes:
            permission = permissions[permission_code]
            key = (role.id, permission.id)

            if key in existing_links:
                continue

            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )
            existing_links.add(key)


async def seed_system_data(
    session: AsyncSession,
) -> None:
    company = await seed_default_company(session)
    await seed_main_branch(session, company)

    roles = await seed_roles(session)
    permissions = await seed_permissions(session)

    await seed_role_permissions(
        session=session,
        roles=roles,
        permissions=permissions,
    )

    await session.commit()
