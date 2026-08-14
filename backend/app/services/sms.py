from __future__ import annotations

import re


class SmsConfigurationError(RuntimeError):
    """Raised when SMS configuration is invalid."""


class SmsPhoneError(ValueError):
    """Raised when an SMS recipient number is invalid."""


def normalize_sri_lankan_phone(
    value: str,
) -> str:
    """
    Normalize a Sri Lankan mobile number to +94XXXXXXXXX.

    Accepted examples:
        0771234567
        94771234567
        +94771234567
        077 123 4567
    """

    raw = (value or "").strip()

    if not raw:
        raise SmsPhoneError(
            "SMS recipient phone number is required"
        )

    compact = re.sub(
        r"[\s()\-]",
        "",
        raw,
    )

    if compact.startswith("+"):
        digits = compact[1:]
    else:
        digits = compact

    if not digits.isdigit():
        raise SmsPhoneError(
            "SMS recipient phone number is invalid"
        )

    if (
        len(digits) == 10
        and digits.startswith("0")
    ):
        digits = "94" + digits[1:]

    elif (
        len(digits) == 9
        and digits.startswith("7")
    ):
        digits = "94" + digits

    if (
        len(digits) != 11
        or not digits.startswith("947")
    ):
        raise SmsPhoneError(
            "SMS recipient must be a valid "
            "Sri Lankan mobile number"
        )

    return "+" + digits


from dataclasses import dataclass
from typing import Any

import httpx


class SmsProviderError(RuntimeError):
    """Raised when the SMS provider rejects or fails a request."""


@dataclass(slots=True)
class SmsSendResult:
    provider: str
    success: bool
    status: str
    campaign_id: str | None
    pages: int | None
    recipient_number: str | None
    sms_credit_balance: str | None
    charged_from: str | None
    raw_response: dict[str, Any]


class SmslenzClient:
    def __init__(
        self,
        *,
        base_url: str,
        user_id: str,
        api_key: str,
        sender_id: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id.strip()
        self.api_key = api_key.strip()
        self.sender_id = sender_id.strip()
        self.timeout_seconds = timeout_seconds
        self.transport = transport

        if not self.user_id:
            raise SmsConfigurationError(
                "SMSlenz user ID is required"
            )

        if not self.api_key:
            raise SmsConfigurationError(
                "SMSlenz API key is required"
            )

        if not self.sender_id:
            raise SmsConfigurationError(
                "SMSlenz sender ID is required"
            )

    async def send_sms(
        self,
        *,
        contact: str,
        message: str,
    ) -> SmsSendResult:
        normalized_contact = (
            normalize_sri_lankan_phone(
                contact
            )
        )

        clean_message = (
            message or ""
        ).strip()

        if not clean_message:
            raise ValueError(
                "SMS message is required"
            )

        if len(clean_message) > 1500:
            raise ValueError(
                "SMS message cannot exceed 1500 characters"
            )

        payload = {
            "user_id":
                self.user_id,
            "api_key":
                self.api_key,
            "sender_id":
                self.sender_id,
            "contact":
                normalized_contact,
            "message":
                clean_message,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/send-sms",
                    json=payload,
                    headers={
                        "Accept":
                            "application/json",
                        "Content-Type":
                            "application/json",
                    },
                )

        except httpx.TimeoutException as exc:
            raise SmsProviderError(
                "SMSlenz request timed out"
            ) from exc

        except httpx.HTTPError as exc:
            raise SmsProviderError(
                "SMSlenz request failed"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise SmsProviderError(
                "SMSlenz returned invalid JSON"
            ) from exc

        if response.status_code >= 400:
            detail = (
                body.get("message")
                if isinstance(
                    body,
                    dict,
                )
                else None
            )

            raise SmsProviderError(
                detail
                or (
                    "SMSlenz returned HTTP "
                    f"{response.status_code}"
                )
            )

        if not isinstance(
            body,
            dict,
        ):
            raise SmsProviderError(
                "SMSlenz response format is invalid"
            )

        success = bool(
            body.get("success")
        )

        data = body.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            data = {}

        provider_status = str(
            data.get(
                "status",
                "",
            )
        ).strip()

        if (
            not success
            or provider_status.lower()
            not in {
                "success",
                "sent",
            }
        ):
            raise SmsProviderError(
                str(
                    body.get(
                        "message",
                        "SMSlenz rejected the SMS request",
                    )
                )
            )

        campaign_value = data.get(
            "campaign_id"
        )

        campaign_id = (
            str(campaign_value)
            if campaign_value
            is not None
            else None
        )

        pages_value = data.get(
            "pages"
        )

        try:
            pages = (
                int(pages_value)
                if pages_value
                is not None
                else None
            )
        except (
            TypeError,
            ValueError,
        ):
            pages = None

        recipient_number = data.get(
            "recipient_number"
        )

        if recipient_number is not None:
            recipient_number = str(
                recipient_number
            )

        sms_credit_balance = data.get(
            "sms_credit_balance"
        )

        if sms_credit_balance is not None:
            sms_credit_balance = str(
                sms_credit_balance
            )

        charged_from = data.get(
            "charged_from"
        )

        if charged_from is not None:
            charged_from = str(
                charged_from
            )

        return SmsSendResult(
            provider="smslenz",
            success=True,
            status=provider_status,
            campaign_id=campaign_id,
            pages=pages,
            recipient_number=(
                recipient_number
            ),
            sms_credit_balance=(
                sms_credit_balance
            ),
            charged_from=(
                charged_from
            ),
            raw_response=body,
        )


# ============================================================
# SMS OUTBOX / OWNER JOB REMINDERS
# ============================================================

from datetime import date, datetime, time, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.service import ServiceJobCard
from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)


OWNER_JOB_REMINDER_EVENT = "owner_job_visit_reminder"


def build_owner_job_reminder_key(
    *,
    company_id: int,
    job_card_id: int,
    visit_date: date,
) -> str:
    """
    Stable once-only key for one owner reminder
    for one job and scheduled visit date.
    """

    return (
        f"owner-job-reminder:"
        f"{company_id}:"
        f"{job_card_id}:"
        f"{visit_date.isoformat()}"
    )


def build_owner_job_reminder_message(
    *,
    job_number: str,
    visit_date: date,
    today: date,
) -> str:
    if visit_date == today:
        day_label = "today"
    elif visit_date == today + timedelta(days=1):
        day_label = "tomorrow"
    else:
        day_label = visit_date.isoformat()

    return (
        f"Service reminder: {job_number} "
        f"is scheduled for {day_label} "
        f"({visit_date.isoformat()})."
    )


async def queue_owner_job_reminders(
    session: AsyncSession,
    *,
    company_id: int,
    today: date | None = None,
) -> list[SmsNotification]:
    """
    Queue owner SMS reminders for service jobs scheduled
    today or tomorrow.

    This function DOES NOT send SMS messages.

    Duplicate reminders are prevented using the
    sms_notifications deduplication key.
    """

    effective_today = today or date.today()
    tomorrow = effective_today + timedelta(days=1)

    company = (
        await session.execute(
            select(Company).where(
                Company.id == company_id
            )
        )
    ).scalar_one_or_none()

    if company is None:
        return []

    raw_owner_phone = (
        company.owner_sms_phone or ""
    ).strip()

    if not raw_owner_phone:
        return []

    owner_phone = normalize_sri_lankan_phone(
        raw_owner_phone
    )

    jobs = (
        await session.execute(
            select(ServiceJobCard)
            .where(
                ServiceJobCard.company_id
                == company_id,
                ServiceJobCard.scheduled_visit_date.in_(
                    [
                        effective_today,
                        tomorrow,
                    ]
                ),
            )
            .order_by(
                ServiceJobCard.scheduled_visit_date,
                ServiceJobCard.id,
            )
        )
    ).scalars().all()

    queued: list[SmsNotification] = []

    for job in jobs:
        if (
            job.id is None
            or not job.job_number
            or job.scheduled_visit_date is None
        ):
            continue

        deduplication_key = (
            build_owner_job_reminder_key(
                company_id=company_id,
                job_card_id=job.id,
                visit_date=(
                    job.scheduled_visit_date
                ),
            )
        )

        existing_id = (
            await session.execute(
                select(SmsNotification.id)
                .where(
                    SmsNotification
                    .deduplication_key
                    == deduplication_key
                )
            )
        ).scalar_one_or_none()

        if existing_id is not None:
            continue

        message = (
            build_owner_job_reminder_message(
                job_number=job.job_number,
                visit_date=(
                    job.scheduled_visit_date
                ),
                today=effective_today,
            )
        )

        notification = SmsNotification(
            company_id=company_id,
            job_card_id=job.id,
            customer_id=job.customer_id,
            recipient_type=(
                SmsRecipientType.OWNER.value
            ),
            recipient_phone=owner_phone,
            event_type=(
                OWNER_JOB_REMINDER_EVENT
            ),
            message=message,
            status=(
                SmsNotificationStatus.PENDING.value
            ),
            deduplication_key=(
                deduplication_key
            ),
            provider_message_id=None,
            attempt_count=0,
            last_error=None,
            scheduled_for=datetime.combine(
                effective_today,
                time.min,
            ),
            sent_at=None,
        )

        session.add(notification)

        # Flush immediately so duplicate-key and other
        # DB contract problems are detected here.
        await session.flush()

        queued.append(notification)

    return queued


# ============================================================
# CUSTOMER SERVICE STATUS SMS OUTBOX
# ============================================================

from app.models.customer import Customer


CUSTOMER_SERVICE_STATUS_EVENTS = {
    "waiting_approval":
        "customer_service_waiting_approval",
    "repairing":
        "customer_service_repairing",
    "ready":
        "customer_service_ready",
    "delivered":
        "customer_service_delivered",
}


def build_customer_service_status_key(
    *,
    company_id: int,
    job_card_id: int,
    status_value: str,
) -> str:
    """
    Stable once-only key for a customer notification
    for one service-job status.
    """

    return (
        "customer-service-status:"
        f"{company_id}:"
        f"{job_card_id}:"
        f"{status_value}"
    )


def build_customer_service_status_message(
    *,
    job_number: str,
    status_value: str,
) -> str:
    """
    Customer-facing English SMS text.

    Keep messages concise because provider SMS billing
    can depend on message length / segment count.
    """

    messages = {
        "waiting_approval": (
            f"Service update: {job_number} is awaiting "
            "your approval. Please contact us for details."
        ),
        "repairing": (
            f"Service update: repair work has started "
            f"for {job_number}."
        ),
        "ready": (
            f"Service update: {job_number} is ready "
            "for collection. Please contact us if needed."
        ),
        "delivered": (
            f"Service update: {job_number} has been "
            "delivered. Thank you."
        ),
    }

    try:
        return messages[status_value]
    except KeyError as exc:
        raise ValueError(
            "Unsupported customer service SMS status"
        ) from exc


async def queue_customer_service_status_notification(
    session: AsyncSession,
    *,
    job: ServiceJobCard,
    status_value: str,
) -> SmsNotification | None:
    """
    Queue a customer SMS notification for a supported
    service-job status.

    This function DOES NOT call the SMS provider.

    Missing consent, missing customer, invalid phone,
    unsupported status, or an existing deduplication key
    results in no notification.

    Customer SMS problems must not prevent the service-job
    lifecycle itself from continuing.
    """

    event_type = CUSTOMER_SERVICE_STATUS_EVENTS.get(
        status_value
    )

    if event_type is None:
        return None

    if (
        job.id is None
        or not job.job_number
        or job.customer_id is None
    ):
        return None

    customer = (
        await session.execute(
            select(Customer).where(
                Customer.id == job.customer_id,
                Customer.company_id == job.company_id,
            )
        )
    ).scalar_one_or_none()

    if customer is None:
        return None

    if not customer.sms_allowed:
        return None

    raw_phone = (
        customer.sms_phone or ""
    ).strip()

    if not raw_phone:
        return None

    try:
        recipient_phone = (
            normalize_sri_lankan_phone(
                raw_phone
            )
        )
    except SmsPhoneError:
        # Invalid SMS contact data must not break
        # the service-job transaction.
        return None

    deduplication_key = (
        build_customer_service_status_key(
            company_id=job.company_id,
            job_card_id=job.id,
            status_value=status_value,
        )
    )

    existing_id = (
        await session.execute(
            select(SmsNotification.id).where(
                SmsNotification.deduplication_key
                == deduplication_key
            )
        )
    ).scalar_one_or_none()

    if existing_id is not None:
        return None

    notification = SmsNotification(
        company_id=job.company_id,
        job_card_id=job.id,
        customer_id=customer.id,
        recipient_type=(
            SmsRecipientType.CUSTOMER.value
        ),
        recipient_phone=recipient_phone,
        event_type=event_type,
        message=(
            build_customer_service_status_message(
                job_number=job.job_number,
                status_value=status_value,
            )
        ),
        status=(
            SmsNotificationStatus.PENDING.value
        ),
        deduplication_key=deduplication_key,
        provider_message_id=None,
        attempt_count=0,
        last_error=None,
        scheduled_for=datetime.now(),
        sent_at=None,
    )

    session.add(notification)

    await session.flush()

    return notification

# ============================================================
# SMS DISPATCHER
# ============================================================

from datetime import datetime as _sms_datetime, timedelta as _sms_timedelta

from app.core.config import get_settings


async def claim_sms_notification_for_processing(
    session: AsyncSession,
    *,
    notification_id: int,
    commit_claim: bool = False,
) -> bool:
    """
    Atomically claim one pending SMS notification.

    The conditional UPDATE is the concurrency boundary:
    only a row that is still PENDING may become PROCESSING.

    Returns True only for the worker that successfully
    claimed the row.
    """

    now = _sms_datetime.now()

    result = await session.execute(
        update(SmsNotification)
        .where(
            SmsNotification.id == notification_id,
            SmsNotification.status
            == SmsNotificationStatus.PENDING.value,
            (
                SmsNotification.scheduled_for.is_(None)
                | (
                    SmsNotification.scheduled_for
                    <= now
                )
            ),
        )
        .values(
            status=(
                SmsNotificationStatus.PROCESSING.value
            ),
            processing_started_at=now,
            attempt_count=(
                SmsNotification.attempt_count + 1
            ),
            last_error=None,
        )
    )

    await session.flush()

    claimed = result.rowcount == 1

    if commit_claim:
        if claimed:
            await session.commit()
        else:
            await session.rollback()

    return claimed


async def dispatch_sms_notification(
    session: AsyncSession,
    *,
    notification: SmsNotification,
    client: SmslenzClient | None = None,
    already_claimed: bool = False,
) -> SmsNotification:
    """
    Dispatch one SMS outbox notification.

    Safety rules:
    - A normal dispatch must atomically claim PENDING first.
    - An already-claimed row must already be PROCESSING.
    - attempt_count increments only during atomic claim.
    - processing_started_at represents the active lease.
    - SENT rows are never resent.
    """

    effective_client = client

    if effective_client is None:
        settings = get_settings()

        if not settings.sms_enabled:
            return notification

        effective_client = SmslenzClient(
            base_url=settings.sms_base_url,
            user_id=settings.sms_user_id,
            api_key=settings.sms_api_key,
            sender_id=settings.sms_sender_id,
            timeout_seconds=(
                settings.sms_timeout_seconds
            ),
        )

    if already_claimed:
        if (
            notification.status
            != SmsNotificationStatus.PROCESSING.value
        ):
            return notification

    else:
        if (
            notification.status
            != SmsNotificationStatus.PENDING.value
        ):
            return notification

        claimed = (
            await claim_sms_notification_for_processing(
                session,
                notification_id=notification.id,
                commit_claim=True,
            )
        )

        if not claimed:
            await session.refresh(notification)
            return notification

        await session.refresh(notification)

    try:
        result = await effective_client.send_sms(
            contact=notification.recipient_phone,
            message=notification.message,
        )

    except Exception as exc:
        notification.status = (
            SmsNotificationStatus.FAILED.value
        )

        notification.last_error = str(exc)
        notification.provider_message_id = None
        notification.sent_at = None
        notification.processing_started_at = None

        await session.flush()
        await session.commit()

        return notification

    notification.status = (
        SmsNotificationStatus.SENT.value
    )

    notification.provider_message_id = (
        result.campaign_id
    )

    notification.last_error = None
    notification.sent_at = _sms_datetime.now()
    notification.processing_started_at = None

    await session.flush()
    await session.commit()

    return notification


async def dispatch_pending_sms_notifications(
    session: AsyncSession,
    *,
    client: SmslenzClient | None = None,
    limit: int = 50,
) -> list[SmsNotification]:
    """
    Claim and dispatch due pending SMS notifications.

    Candidate selection itself does not grant ownership.
    Every row must pass the conditional atomic claim before
    any provider request may occur.

    No commit is performed here. Transaction ownership stays
    with the caller.
    """

    if limit < 1:
        return []

    effective_client = client

    if effective_client is None:
        settings = get_settings()

        if not settings.sms_enabled:
            return []

        effective_client = SmslenzClient(
            base_url=settings.sms_base_url,
            user_id=settings.sms_user_id,
            api_key=settings.sms_api_key,
            sender_id=settings.sms_sender_id,
            timeout_seconds=(
                settings.sms_timeout_seconds
            ),
        )

    now = _sms_datetime.now()

    candidate_ids = (
        await session.execute(
            select(SmsNotification.id)
            .where(
                SmsNotification.status
                == SmsNotificationStatus.PENDING.value,
                (
                    SmsNotification.scheduled_for.is_(None)
                    | (
                        SmsNotification.scheduled_for
                        <= now
                    )
                ),
            )
            .order_by(
                SmsNotification.id
            )
            .limit(limit)
        )
    ).scalars().all()

    dispatched: list[SmsNotification] = []

    for notification_id in candidate_ids:
        claimed = (
            await claim_sms_notification_for_processing(
                session,
                notification_id=notification_id,
                commit_claim=True,
            )
        )

        if not claimed:
            continue

        notification = await session.get(
            SmsNotification,
            notification_id,
            populate_existing=True,
        )

        if notification is None:
            continue

        result = await dispatch_sms_notification(
            session,
            notification=notification,
            client=effective_client,
            already_claimed=True,
        )

        dispatched.append(result)

    return dispatched


# ============================================================
# SMS RETRY POLICY
# ============================================================

SMS_PROCESSING_LEASE_SECONDS = 300


async def recover_stale_processing_sms_notifications(
    session: AsyncSession,
    *,
    now: _sms_datetime | None = None,
    lease_seconds: int = SMS_PROCESSING_LEASE_SECONDS,
    commit_recovery: bool = False,
) -> int:
    """
    Recover SMS rows whose PROCESSING lease expired.

    Safety policy:
    stale PROCESSING rows become FAILED, not PENDING.

    A process may have successfully submitted an SMS to the
    provider and crashed before recording SENT. Automatically
    retrying that row could send a duplicate SMS.

    Explicit retry policy must be used after review.
    """

    if lease_seconds < 1:
        raise ValueError(
            "lease_seconds must be at least 1"
        )

    effective_now = now or _sms_datetime.now()

    cutoff = (
        effective_now
        - _sms_timedelta(
            seconds=lease_seconds
        )
    )

    result = await session.execute(
        update(SmsNotification)
        .where(
            SmsNotification.status
            == SmsNotificationStatus.PROCESSING.value,
            SmsNotification.processing_started_at
            .is_not(None),
            SmsNotification.processing_started_at
            <= cutoff,
        )
        .values(
            status=(
                SmsNotificationStatus.FAILED.value
            ),
            processing_started_at=None,
            provider_message_id=None,
            sent_at=None,
            last_error=(
                "SMS processing lease expired; "
                "delivery outcome unknown; "
                "manual retry required"
            ),
        )
    )

    await session.flush()

    recovered = int(
        result.rowcount or 0
    )

    if commit_recovery:
        await session.commit()

    return recovered


SMS_MAX_ATTEMPTS = 3


def retry_failed_sms_notification(
    notification: SmsNotification,
    *,
    max_attempts: int = SMS_MAX_ATTEMPTS,
) -> bool:
    """
    Move an eligible failed SMS back to pending.

    Returns True only when the notification was re-queued.

    Safety:
    - only FAILED rows may be retried
    - SENT rows are never retried
    - attempt_count is not incremented here
    - dispatcher increments attempt_count only when an actual
      provider attempt starts
    """

    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be at least 1"
        )

    if (
        notification.status
        != SmsNotificationStatus.FAILED.value
    ):
        return False

    attempts = notification.attempt_count or 0

    if attempts >= max_attempts:
        return False

    notification.status = (
        SmsNotificationStatus.PENDING.value
    )

    notification.provider_message_id = None
    notification.sent_at = None
    notification.processing_started_at = None

    return True
