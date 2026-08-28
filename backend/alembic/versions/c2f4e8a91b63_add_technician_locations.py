"""add technician locations

Revision ID: c2f4e8a91b63
Revises: af54a247c8ed
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = (
    "c2f4e8a91b63"
)

down_revision: (
    str | Sequence[str] | None
) = "af54a247c8ed"

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    op.create_table(
        "technician_locations",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "technician_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "service_job_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(
                precision=9,
                scale=6,
            ),
            nullable=True,
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
            "client_recorded_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=True,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=(
                sa.text("now()")
            ),
            nullable=False,
        ),
        sa.Column(
            "tracking_state",
            sa.String(
                length=20
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(
                length=50
            ),
            server_default=(
                "technician_web_portal"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "tracking_state IN "
                "('active', 'stopped')"
            ),
            name=(
                "ck_technician_locations_"
                "tracking_state"
            ),
        ),
        sa.ForeignKeyConstraint(
            [
                "service_job_id"
            ],
            [
                "service_job_cards.id"
            ],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            [
                "technician_id"
            ],
            [
                "users.id"
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "technician_id",
            name=(
                "uq_technician_locations_"
                "technician_id"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_technician_locations_"
            "technician_id"
        ),
        "technician_locations",
        [
            "technician_id"
        ],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_technician_locations_"
            "service_job_id"
        ),
        "technician_locations",
        [
            "service_job_id"
        ],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_technician_locations_"
            "recorded_at"
        ),
        "technician_locations",
        [
            "recorded_at"
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_technician_locations_"
            "recorded_at"
        ),
        table_name=(
            "technician_locations"
        ),
    )

    op.drop_index(
        op.f(
            "ix_technician_locations_"
            "service_job_id"
        ),
        table_name=(
            "technician_locations"
        ),
    )

    op.drop_index(
        op.f(
            "ix_technician_locations_"
            "technician_id"
        ),
        table_name=(
            "technician_locations"
        ),
    )

    op.drop_table(
        "technician_locations"
    )
