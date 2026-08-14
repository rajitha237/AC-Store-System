"""add installment interest fields

Revision ID: 428f30d7f939
Revises: 3bf2590550f8
Create Date: 2026-08-14 18:55:32.981391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '428f30d7f939'
down_revision: Union[str, Sequence[str], None] = '3bf2590550f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add installment principal and interest fields."""

    with op.batch_alter_table(
        "installment_plans",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "principal_amount",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "interest_rate",
                sa.Numeric(
                    precision=8,
                    scale=4,
                ),
                nullable=False,
                server_default="0.0000",
            )
        )

        batch_op.add_column(
            sa.Column(
                "interest_amount",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=False,
                server_default="0.00",
            )
        )

    op.execute(
        """
        UPDATE installment_plans
        SET principal_amount = financed_amount
        WHERE principal_amount IS NULL
        """
    )

    with op.batch_alter_table(
        "installment_plans",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "principal_amount",
            existing_type=sa.Numeric(
                precision=18,
                scale=2,
            ),
            nullable=False,
        )

    with op.batch_alter_table(
        "installment_payment_allocations",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "principal_amount",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=False,
                server_default="0.00",
            )
        )

        batch_op.add_column(
            sa.Column(
                "interest_amount",
                sa.Numeric(
                    precision=18,
                    scale=2,
                ),
                nullable=False,
                server_default="0.00",
            )
        )

    op.execute(
        """
        UPDATE installment_payment_allocations
        SET principal_amount = amount,
            interest_amount = 0.00
        """
    )


def downgrade() -> None:
    """Remove installment principal and interest fields."""

    with op.batch_alter_table(
        "installment_payment_allocations",
        schema=None,
    ) as batch_op:
        batch_op.drop_column(
            "interest_amount"
        )
        batch_op.drop_column(
            "principal_amount"
        )

    with op.batch_alter_table(
        "installment_plans",
        schema=None,
    ) as batch_op:
        batch_op.drop_column(
            "interest_amount"
        )
        batch_op.drop_column(
            "interest_rate"
        )
        batch_op.drop_column(
            "principal_amount"
        )
