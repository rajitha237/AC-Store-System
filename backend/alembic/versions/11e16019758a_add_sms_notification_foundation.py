"""add sms notification foundation

Revision ID: 11e16019758a
Revises: 428f30d7f939
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "11e16019758a"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "428f30d7f939"
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
    with op.batch_alter_table(
        "service_job_cards"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "scheduled_visit_date",
                sa.Date(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_service_job_cards_scheduled_visit_date",
            ["scheduled_visit_date"],
            unique=False,
        )

    with op.batch_alter_table(
        "companies"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_sms_phone",
                sa.String(length=20),
                nullable=True,
            )
        )

    op.create_table(
        "sms_notifications",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "job_card_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "recipient_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "recipient_phone",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=60),
            nullable=False,
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "deduplication_key",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "provider_message_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
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
            ["job_card_id"],
            ["service_job_cards.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "deduplication_key",
            name=(
                "uq_sms_notifications_"
                "deduplication_key"
            ),
        ),
    )

    op.create_index(
        "ix_sms_notifications_company_id",
        "sms_notifications",
        ["company_id"],
        unique=False,
    )

    op.create_index(
        "ix_sms_notifications_job_card_id",
        "sms_notifications",
        ["job_card_id"],
        unique=False,
    )

    op.create_index(
        "ix_sms_notifications_customer_id",
        "sms_notifications",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        "ix_sms_notifications_status",
        "sms_notifications",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_sms_notifications_event_type",
        "sms_notifications",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_sms_notifications_scheduled_for",
        "sms_notifications",
        ["scheduled_for"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sms_notifications_scheduled_for",
        table_name="sms_notifications",
    )

    op.drop_index(
        "ix_sms_notifications_event_type",
        table_name="sms_notifications",
    )

    op.drop_index(
        "ix_sms_notifications_status",
        table_name="sms_notifications",
    )

    op.drop_index(
        "ix_sms_notifications_customer_id",
        table_name="sms_notifications",
    )

    op.drop_index(
        "ix_sms_notifications_job_card_id",
        table_name="sms_notifications",
    )

    op.drop_index(
        "ix_sms_notifications_company_id",
        table_name="sms_notifications",
    )

    op.drop_table(
        "sms_notifications"
    )

    with op.batch_alter_table(
        "companies"
    ) as batch_op:
        batch_op.drop_column(
            "owner_sms_phone"
        )

    with op.batch_alter_table(
        "service_job_cards"
    ) as batch_op:
        batch_op.drop_index(
            "ix_service_job_cards_scheduled_visit_date"
        )

        batch_op.drop_column(
            "scheduled_visit_date"
        )
