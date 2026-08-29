"""add service job location records

Revision ID: d7e31a5b9f42
Revises: c2f4e8a91b63
Create Date: 2026-08-28

"""

from typing import (
    Sequence,
    Union,
)

from alembic import op
import sqlalchemy as sa


revision: str = "d7e31a5b9f42"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "c2f4e8a91b63"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "service_job_location_records",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "service_job_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "technician_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        ),
        sa.Column(
            "accuracy_meters",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(
                timezone=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text(
                "now()"
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["service_job_id"],
            ["service_job_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["technician_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "service_job_id",
            name=(
                "uq_service_job_location_records_"
                "service_job_id"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_service_job_location_records_"
            "service_job_id"
        ),
        "service_job_location_records",
        ["service_job_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_service_job_location_records_"
            "technician_id"
        ),
        "service_job_location_records",
        ["technician_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_service_job_location_records_"
            "completed_at"
        ),
        "service_job_location_records",
        ["completed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_service_job_location_records_"
            "completed_at"
        ),
        table_name=(
            "service_job_location_records"
        ),
    )

    op.drop_index(
        op.f(
            "ix_service_job_location_records_"
            "technician_id"
        ),
        table_name=(
            "service_job_location_records"
        ),
    )

    op.drop_index(
        op.f(
            "ix_service_job_location_records_"
            "service_job_id"
        ),
        table_name=(
            "service_job_location_records"
        ),
    )

    op.drop_table(
        "service_job_location_records"
    )
