"""add legacy service job management status

Revision ID: 4d8821da5e87
Revises: 7aa39b7a85aa
Create Date: 2026-08-18 08:59:25.205086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d8821da5e87'
down_revision: str | None = "7aa39b7a85aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "legacy_service_jobs",
        sa.Column(
            "management_status",
            sa.String(length=50),
            nullable=False,
            server_default="received",
        ),
    )

    op.add_column(
        "legacy_service_jobs",
        sa.Column(
            "status_remarks",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "legacy_service_jobs",
        sa.Column(
            "status_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "legacy_service_jobs",
        sa.Column(
            "status_updated_by_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_legacy_service_jobs_management_status",
        "legacy_service_jobs",
        ["management_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legacy_service_jobs_management_status",
        table_name="legacy_service_jobs",
    )

    op.drop_column(
        "legacy_service_jobs",
        "status_updated_by_id",
    )

    op.drop_column(
        "legacy_service_jobs",
        "status_updated_at",
    )

    op.drop_column(
        "legacy_service_jobs",
        "status_remarks",
    )

    op.drop_column(
        "legacy_service_jobs",
        "management_status",
    )
