"""add service job completion evidence

Revision ID: 75e5e5130acb
Revises: d7e31a5b9f42
Create Date: 2026-08-31 07:45:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "75e5e5130acb"
down_revision: Union[str, Sequence[str], None] = "d7e31a5b9f42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_completion_evidence",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "job_card_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "evidence_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "content",
            sa.LargeBinary(),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_card_id"],
            ["service_job_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_card_id",
            "evidence_type",
            "sequence_number",
            name=(
                "uq_service_completion_evidence_"
                "job_type_sequence"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_service_completion_evidence_job_card_id"
        ),
        "service_completion_evidence",
        ["job_card_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_service_completion_evidence_evidence_type"
        ),
        "service_completion_evidence",
        ["evidence_type"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_service_completion_evidence_uploaded_by_id"
        ),
        "service_completion_evidence",
        ["uploaded_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_service_completion_evidence_uploaded_by_id"
        ),
        table_name="service_completion_evidence",
    )

    op.drop_index(
        op.f(
            "ix_service_completion_evidence_evidence_type"
        ),
        table_name="service_completion_evidence",
    )

    op.drop_index(
        op.f(
            "ix_service_completion_evidence_job_card_id"
        ),
        table_name="service_completion_evidence",
    )

    op.drop_table(
        "service_completion_evidence"
    )
