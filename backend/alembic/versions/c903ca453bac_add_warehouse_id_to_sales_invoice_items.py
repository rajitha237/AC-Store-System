"""add warehouse id to sales invoice items

Revision ID: c903ca453bac
Revises: 4d8821da5e87
Create Date: 2026-08-18 13:02:55.943871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c903ca453bac'
down_revision: Union[str, Sequence[str], None] = '4d8821da5e87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist selected warehouse on sales invoice items."""

    op.add_column(
        "sales_invoice_items",
        sa.Column(
            "warehouse_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_sales_invoice_items_warehouse_id_warehouses",
        "sales_invoice_items",
        "warehouses",
        ["warehouse_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_sales_invoice_items_warehouse_id",
        "sales_invoice_items",
        ["warehouse_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove sales invoice item warehouse persistence."""

    op.drop_index(
        "ix_sales_invoice_items_warehouse_id",
        table_name="sales_invoice_items",
    )

    op.drop_constraint(
        "fk_sales_invoice_items_warehouse_id_warehouses",
        "sales_invoice_items",
        type_="foreignkey",
    )

    op.drop_column(
        "sales_invoice_items",
        "warehouse_id",
    )

