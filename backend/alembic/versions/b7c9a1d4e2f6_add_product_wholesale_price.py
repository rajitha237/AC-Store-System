"""add product wholesale price

Revision ID: b7c9a1d4e2f6
Revises: 877748e87094
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c9a1d4e2f6"
down_revision: Union[str, Sequence[str], None] = (
    "877748e87094"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "wholesale_price",
            sa.Numeric(
                precision=18,
                scale=2,
            ),
            server_default="0.00",
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE products
        SET wholesale_price = selling_price
        """
    )

    op.create_check_constraint(
        "ck_products_wholesale_price_nonnegative",
        "products",
        "wholesale_price >= 0",
    )

    op.create_check_constraint(
        "ck_products_minimum_not_above_wholesale",
        "products",
        "minimum_selling_price <= wholesale_price",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_products_ck_products_minimum_not_above_wholesale",
        "products",
        type_="check",
    )

    op.drop_constraint(
        "ck_products_ck_products_wholesale_price_nonnegative",
        "products",
        type_="check",
    )

    op.drop_column(
        "products",
        "wholesale_price",
    )
