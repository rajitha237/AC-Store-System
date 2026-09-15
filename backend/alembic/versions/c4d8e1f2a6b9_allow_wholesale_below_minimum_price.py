"""allow wholesale price below minimum selling price

Revision ID: c4d8e1f2a6b9
Revises: b7c9a1d4e2f6
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c4d8e1f2a6b9"
down_revision: str | Sequence[str] | None = "b7c9a1d4e2f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f(
            "ck_products_ck_products_minimum_not_above_wholesale"
        ),
        "products",
        type_="check",
    )


def downgrade() -> None:
    op.create_check_constraint(
        "ck_products_minimum_not_above_wholesale",
        "products",
        "minimum_selling_price <= wholesale_price",
    )
