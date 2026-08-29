from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class ServiceJobLocationRecord(Base):
    """
    Permanent location snapshot captured when a
    technician completes an assigned service job.

    This is intentionally separate from
    TechnicianLocation, which remains latest-only.
    """

    __tablename__ = (
        "service_job_location_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "service_job_id",
            name=(
                "uq_service_job_location_records_"
                "service_job_id"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    service_job_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "service_job_cards.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    technician_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "users.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
            index=True,
        )
    )

    latitude: Mapped[Decimal] = (
        mapped_column(
            Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        )
    )

    longitude: Mapped[Decimal] = (
        mapped_column(
            Numeric(
                precision=9,
                scale=6,
            ),
            nullable=False,
        )
    )

    accuracy_meters: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(
            precision=10,
            scale=2,
        ),
        nullable=True,
    )

    completed_at: Mapped[datetime] = (
        mapped_column(
            DateTime(
                timezone=True,
            ),
            nullable=False,
            index=True,
        )
    )

    recorded_at: Mapped[datetime] = (
        mapped_column(
            DateTime(
                timezone=True,
            ),
            server_default=func.now(),
            nullable=False,
        )
    )
