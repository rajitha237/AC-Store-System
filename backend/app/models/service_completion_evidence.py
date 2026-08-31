from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ServiceCompletionEvidence(Base):
    __tablename__ = "service_completion_evidence"

    __table_args__ = (
        UniqueConstraint(
            "job_card_id",
            "evidence_type",
            "sequence_number",
            name="uq_service_completion_evidence_job_type_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_card_id: Mapped[int] = mapped_column(
        ForeignKey(
            "service_job_cards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    content: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
