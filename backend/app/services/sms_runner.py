from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.company import Company
from app.services.sms import (
    dispatch_pending_sms_notifications,
    queue_installment_due_reminders,
    queue_owner_job_reminders,
    recover_stale_processing_sms_notifications,
)


logger = logging.getLogger("uvicorn.error")


@dataclass(slots=True)
class SmsCycleResult:
    enabled: bool
    companies_checked: int = 0
    owner_reminders_queued: int = 0
    installment_reminders_queued: int = 0
    stale_rows_recovered: int = 0
    notifications_dispatched: int = 0


def _company_local_date(
    timezone_name: str | None,
):
    name = (
        (timezone_name or "").strip()
        or "Asia/Colombo"
    )

    try:
        timezone = ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Invalid company timezone %s; "
            "falling back to Asia/Colombo",
            name,
        )

        timezone = ZoneInfo(
            "Asia/Colombo"
        )

    return datetime.now(
        timezone
    ).date()


async def run_sms_cycle() -> SmsCycleResult:
    """
    Run one automatic SMS cycle.

    When SMS_ENABLED is false this function is a no-op.

    Each company gets its own transaction so one company's
    bad data cannot roll back another company's reminders.
    """

    settings = get_settings()

    if not settings.sms_enabled:
        return SmsCycleResult(
            enabled=False
        )

    result = SmsCycleResult(
        enabled=True
    )

    # Recover abandoned PROCESSING leases first.
    # Safety policy in sms.py marks them FAILED rather than
    # automatically retrying them, avoiding duplicate sends.
    async with AsyncSessionLocal() as session:
        result.stale_rows_recovered = (
            await recover_stale_processing_sms_notifications(
                session,
                commit_recovery=True,
            )
        )

    async with AsyncSessionLocal() as session:
        company_rows = (
            await session.execute(
                select(
                    Company.id,
                    Company.timezone,
                )
                .where(
                    Company.is_active.is_(
                        True
                    )
                )
                .order_by(
                    Company.id
                )
            )
        ).all()

    result.companies_checked = len(
        company_rows
    )

    for company_id, timezone_name in company_rows:
        today = _company_local_date(
            timezone_name
        )

        async with AsyncSessionLocal() as session:
            try:
                owner_rows = (
                    await queue_owner_job_reminders(
                        session,
                        company_id=company_id,
                        today=today,
                    )
                )

                installment_rows = (
                    await queue_installment_due_reminders(
                        session,
                        company_id=company_id,
                        today=today,
                    )
                )

                await session.commit()

                result.owner_reminders_queued += len(
                    owner_rows
                )

                result.installment_reminders_queued += len(
                    installment_rows
                )

            except Exception:
                await session.rollback()

                logger.exception(
                    "SMS reminder queue failed "
                    "for company_id=%s",
                    company_id,
                )

    # Customer service received/ready notifications are queued
    # by the service workflow itself. This dispatcher handles
    # those rows plus the reminder rows queued above.
    async with AsyncSessionLocal() as session:
        dispatched = (
            await dispatch_pending_sms_notifications(
                session,
                limit=(
                    settings.sms_dispatch_limit
                ),
            )
        )

        result.notifications_dispatched = len(
            dispatched
        )

    return result


async def sms_worker_loop() -> None:
    """
    Continuously execute SMS cycles while the application runs.
    """

    settings = get_settings()

    interval_seconds = max(
        10,
        settings.sms_worker_interval_seconds,
    )

    logger.info(
        "SMS worker started; interval=%ss",
        interval_seconds,
    )

    try:
        while True:
            try:
                result = (
                    await run_sms_cycle()
                )

                if result.enabled:
                    logger.info(
                        "SMS cycle complete: "
                        "companies=%s "
                        "owner_queued=%s "
                        "installment_queued=%s "
                        "dispatched=%s "
                        "stale_recovered=%s",
                        result.companies_checked,
                        result.owner_reminders_queued,
                        result.installment_reminders_queued,
                        result.notifications_dispatched,
                        result.stale_rows_recovered,
                    )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "SMS worker cycle failed"
                )

            await asyncio.sleep(
                interval_seconds
            )

    finally:
        logger.info(
            "SMS worker stopped"
        )
