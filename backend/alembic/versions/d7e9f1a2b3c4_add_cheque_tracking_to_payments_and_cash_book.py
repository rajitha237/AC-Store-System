"""add cheque tracking to payments and cash book

Revision ID: d7e9f1a2b3c4
Revises: c4d8e1f2a6b9
"""

from alembic import op
import sqlalchemy as sa


revision = "d7e9f1a2b3c4"
down_revision = "c4d8e1f2a6b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_payments",
        sa.Column(
            "cheque_date",
            sa.Date(),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_customer_payments_cheque_date",
        "customer_payments",
        ["cheque_date"],
        unique=False,
    )

    op.add_column(
        "manual_cash_book_entries",
        sa.Column(
            "cheque_date",
            sa.Date(),
            nullable=True,
        ),
    )
    op.add_column(
        "manual_cash_book_entries",
        sa.Column(
            "cheque_status",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.add_column(
        "manual_cash_book_entries",
        sa.Column(
            "cheque_cleared_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "manual_cash_book_entries",
        sa.Column(
            "cheque_cleared_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_manual_cash_book_entries_cheque_status",
        "manual_cash_book_entries",
        "cheque_status IS NULL OR "
        "cheque_status IN ('pending', 'cleared')",
    )

    op.create_foreign_key(
        "fk_manual_cash_book_entries_cheque_cleared_by_id_users",
        "manual_cash_book_entries",
        "users",
        ["cheque_cleared_by_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_manual_cash_book_entries_cheque_date",
        "manual_cash_book_entries",
        ["cheque_date"],
        unique=False,
    )
    op.create_index(
        "ix_manual_cash_book_entries_cheque_status",
        "manual_cash_book_entries",
        ["cheque_status"],
        unique=False,
    )
    op.create_index(
        "ix_manual_cash_book_entries_cheque_cleared_at",
        "manual_cash_book_entries",
        ["cheque_cleared_at"],
        unique=False,
    )
    op.create_index(
        "ix_manual_cash_book_entries_cheque_cleared_by_id",
        "manual_cash_book_entries",
        ["cheque_cleared_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_manual_cash_book_entries_cheque_cleared_by_id",
        table_name="manual_cash_book_entries",
    )
    op.drop_index(
        "ix_manual_cash_book_entries_cheque_cleared_at",
        table_name="manual_cash_book_entries",
    )
    op.drop_index(
        "ix_manual_cash_book_entries_cheque_status",
        table_name="manual_cash_book_entries",
    )
    op.drop_index(
        "ix_manual_cash_book_entries_cheque_date",
        table_name="manual_cash_book_entries",
    )

    op.drop_constraint(
        "fk_manual_cash_book_entries_cheque_cleared_by_id_users",
        "manual_cash_book_entries",
        type_="foreignkey",
    )

    op.drop_constraint(
        "ck_manual_cash_book_entries_cheque_status",
        "manual_cash_book_entries",
        type_="check",
    )

    op.drop_column(
        "manual_cash_book_entries",
        "cheque_cleared_by_id",
    )
    op.drop_column(
        "manual_cash_book_entries",
        "cheque_cleared_at",
    )
    op.drop_column(
        "manual_cash_book_entries",
        "cheque_status",
    )
    op.drop_column(
        "manual_cash_book_entries",
        "cheque_date",
    )

    op.drop_index(
        "ix_customer_payments_cheque_date",
        table_name="customer_payments",
    )
    op.drop_column(
        "customer_payments",
        "cheque_date",
    )
