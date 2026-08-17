"""add legacy service job history tables

Revision ID: 7aa39b7a85aa
Revises: 19f9943c7b1a
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7aa39b7a85aa'
down_revision: Union[str, Sequence[str], None] = '19f9943c7b1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legacy_service_jobs",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "legacy_job_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "invoice_code",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "job_date",
            sa.Date(),
            nullable=False,
        ),

        sa.Column(
            "job_time",
            sa.Time(),
            nullable=True,
        ),

        sa.Column(
            "reference_no",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "sale_type",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "legacy_customer_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "customer_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "customer_phone",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "customer_address",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "bill_discount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "bill_discount_value",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "source_total",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "net_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "gross_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "profit",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "pay_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "rest_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "cash_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "credit_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "cheque_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "card_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "bank_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "over_balance_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "balance_amount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "is_cancelled",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "legacy_user_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "legacy_user_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "legacy_service_date",
            sa.Date(),
            nullable=True,
        ),

        sa.Column(
            "legacy_warranty_period",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "source_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "source_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "source_payload",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "migration_notes",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "legacy_job_id",
            name="uq_legacy_service_jobs_legacy_job_id",
        ),
    )

    op.create_index(
        "ix_legacy_service_jobs_legacy_job_id",
        "legacy_service_jobs",
        ["legacy_job_id"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_invoice_code",
        "legacy_service_jobs",
        ["invoice_code"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_job_date",
        "legacy_service_jobs",
        ["job_date"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_legacy_customer_id",
        "legacy_service_jobs",
        ["legacy_customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_customer_name",
        "legacy_service_jobs",
        ["customer_name"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_is_cancelled",
        "legacy_service_jobs",
        ["is_cancelled"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_jobs_legacy_service_date",
        "legacy_service_jobs",
        ["legacy_service_date"],
        unique=False,
    )

    op.create_table(
        "legacy_service_job_lines",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "legacy_service_job_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "line_number",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "legacy_code",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "name",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "line_type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "quantity",
            sa.Numeric(18, 3),
            nullable=False,
        ),

        sa.Column(
            "rate",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "discount",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "discount_value",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "line_total",
            sa.Numeric(18, 2),
            nullable=False,
        ),

        sa.Column(
            "unit",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "serial_no",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "source_payload",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["legacy_service_job_id"],
            ["legacy_service_jobs.id"],
            ondelete="RESTRICT",
        ),

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "legacy_service_job_id",
            "line_number",
            name="uq_legacy_service_job_lines_job_line",
        ),
    )

    op.create_index(
        "ix_legacy_service_job_lines_legacy_service_job_id",
        "legacy_service_job_lines",
        ["legacy_service_job_id"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_job_lines_legacy_code",
        "legacy_service_job_lines",
        ["legacy_code"],
        unique=False,
    )

    op.create_index(
        "ix_legacy_service_job_lines_line_type",
        "legacy_service_job_lines",
        ["line_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legacy_service_job_lines_line_type",
        table_name="legacy_service_job_lines",
    )

    op.drop_index(
        "ix_legacy_service_job_lines_legacy_code",
        table_name="legacy_service_job_lines",
    )

    op.drop_index(
        "ix_legacy_service_job_lines_legacy_service_job_id",
        table_name="legacy_service_job_lines",
    )

    op.drop_table(
        "legacy_service_job_lines"
    )

    op.drop_index(
        "ix_legacy_service_jobs_legacy_service_date",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_is_cancelled",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_customer_name",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_legacy_customer_id",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_job_date",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_invoice_code",
        table_name="legacy_service_jobs",
    )

    op.drop_index(
        "ix_legacy_service_jobs_legacy_job_id",
        table_name="legacy_service_jobs",
    )

    op.drop_table(
        "legacy_service_jobs"
    )
