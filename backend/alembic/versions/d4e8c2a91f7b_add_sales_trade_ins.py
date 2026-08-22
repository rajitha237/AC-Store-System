"""add sales trade ins

Revision ID: d4e8c2a91f7b
Revises: fafbb34f4271
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8c2a91f7b"
down_revision: Union[str, None] = "fafbb34f4271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_invoices",
        sa.Column(
            "trade_in_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
    )

    op.create_check_constraint(
        "ck_sales_invoices_trade_in_nonnegative",
        "sales_invoices",
        "trade_in_amount >= 0",
    )

    op.create_table(
        "sales_trade_ins",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey(
                "sales_invoices.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "brand",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "model",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "serial_number",
            sa.String(length=150),
            nullable=True,
        ),
        sa.Column(
            "condition",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "allowance_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "allowance_amount > 0",
            name=(
                "ck_sales_trade_ins_"
                "allowance_positive"
            ),
        ),
    )

    op.create_index(
        "ix_sales_trade_ins_invoice_id",
        "sales_trade_ins",
        ["invoice_id"],
        unique=False,
    )

    op.create_index(
        "ix_sales_trade_ins_serial_number",
        "sales_trade_ins",
        ["serial_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sales_trade_ins_serial_number",
        table_name="sales_trade_ins",
    )

    op.drop_index(
        "ix_sales_trade_ins_invoice_id",
        table_name="sales_trade_ins",
    )

    op.drop_table(
        "sales_trade_ins"
    )

    op.drop_constraint(
        "ck_sales_invoices_trade_in_nonnegative",
        "sales_invoices",
        type_="check",
    )

    op.drop_column(
        "sales_invoices",
        "trade_in_amount",
    )
