"""add sms processing lease timestamp

Revision ID: a6f070650b9f
Revises: 11e16019758a
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a6f070650b9f"
down_revision: str | None = "11e16019758a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table(
        "sms_notifications"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "processing_started_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_sms_notifications_processing_started_at",
            ["processing_started_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "sms_notifications"
    ) as batch_op:
        batch_op.drop_index(
            "ix_sms_notifications_processing_started_at"
        )

        batch_op.drop_column(
            "processing_started_at"
        )
