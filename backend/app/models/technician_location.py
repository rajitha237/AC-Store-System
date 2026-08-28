from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import Base


class TechnicianLocation(Base):
    __tablename__ = (
        "technician_locations"
    )

    __table_args__ = (
        UniqueConstraint(
            "technician_id",
            name=(
                "uq_technician_locations_"
                "technician_id"
            ),
        ),
        CheckConstraint(
            (
                "tracking_state IN "
                "('active', 'stopped')"
            ),
            name=(
                "ck_technician_locations_"
                "tracking_state"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    technician_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    service_job_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    latitude: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
    )

    longitude: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(
            precision=9,
            scale=6,
        ),
        nullable=True,
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

    client_recorded_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(
            timezone=True,
        ),
        nullable=True,
    )

    recorded_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    tracking_state: Mapped[
        str
    ] = mapped_column(
        String(20),
        default="active",
        server_default="active",
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default=(
            "technician_web_portal"
        ),
        server_default=(
            "technician_web_portal"
        ),
        nullable=False,
    )
