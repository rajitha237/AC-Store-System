"""add cash book daily approvals

Revision ID: e8f1a2b3c4d5
Revises: d7e9f1a2b3c4
Create Date: 2026-09-27
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f1a2b3c4d5"
down_revision = "d7e9f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cash_book_daily_approvals",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "business_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "opening_balance",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "cash_in",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "cash_out",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "closing_balance",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "transaction_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "approved_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "company_id",
            "business_date",
            name=(
                "uq_cash_book_daily_approval_"
                "company_date"
            ),
        ),
    )

    op.create_index(
        "ix_cash_book_daily_approvals_company_id",
        "cash_book_daily_approvals",
        ["company_id"],
    )

    op.create_index(
        "ix_cash_book_daily_approvals_business_date",
        "cash_book_daily_approvals",
        ["business_date"],
    )

    op.create_index(
        "ix_cash_book_daily_approvals_approved_by_id",
        "cash_book_daily_approvals",
        ["approved_by_id"],
    )

    op.create_index(
        "ix_cash_book_daily_approvals_company_date",
        "cash_book_daily_approvals",
        ["company_id", "business_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cash_book_daily_approvals_company_date",
        table_name="cash_book_daily_approvals",
    )
    op.drop_index(
        "ix_cash_book_daily_approvals_approved_by_id",
        table_name="cash_book_daily_approvals",
    )
    op.drop_index(
        "ix_cash_book_daily_approvals_business_date",
        table_name="cash_book_daily_approvals",
    )
    op.drop_index(
        "ix_cash_book_daily_approvals_company_id",
        table_name="cash_book_daily_approvals",
    )
    op.drop_table(
        "cash_book_daily_approvals"
    )
