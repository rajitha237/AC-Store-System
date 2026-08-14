from datetime import datetime

import httpx
import pytest
from sqlalchemy import select

from app.models.sms_notification import (
    SmsNotification,
    SmsNotificationStatus,
    SmsRecipientType,
)
from app.services.sms import (
    SmslenzClient,
    dispatch_pending_sms_notifications,
    dispatch_sms_notification,
)


async def create_pending_notification(
    db_session,
    *,
    suffix: str,
) -> SmsNotification:
    notification = SmsNotification(
        company_id=1,
        job_card_id=None,
        customer_id=None,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone="+94771234567",
        event_type="dispatcher_test",
        message=f"Dispatcher test {suffix}",
        status=(
            SmsNotificationStatus.PENDING.value
        ),
        deduplication_key=(
            f"dispatcher-test:{suffix}"
        ),
        provider_message_id=None,
        attempt_count=0,
        last_error=None,
        scheduled_for=datetime.now(),
        sent_at=None,
    )

    db_session.add(notification)
    await db_session.flush()

    return notification


@pytest.mark.asyncio
async def test_dispatch_sms_success(
    db_session,
):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "message": "SMS sent",
                "data": {
                    "status": "success",
                    "campaign_id": "555",
                    "pages": 1,
                    "recipient_number":
                        "94771234567",
                    "sms_credit_balance":
                        "2500.00",
                    "charged_from": "main",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="success",
        )
    )

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
        client=client,
    )

    assert (
        result.status
        == SmsNotificationStatus.SENT.value
    )

    assert result.attempt_count == 1
    assert result.provider_message_id == "555"
    assert result.last_error is None
    assert result.sent_at is not None


@pytest.mark.asyncio
async def test_dispatch_sms_failure(
    db_session,
):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": False,
                "message": "Provider rejected test",
                "data": {
                    "status": "failed",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="failure",
        )
    )

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
        client=client,
    )

    assert (
        result.status
        == SmsNotificationStatus.FAILED.value
    )

    assert result.attempt_count == 1
    assert result.provider_message_id is None
    assert (
        "Provider rejected test"
        in result.last_error
    )
    assert result.sent_at is None


@pytest.mark.asyncio
async def test_dispatch_disabled_without_client(
    db_session,
    monkeypatch,
):
    from app.core.config import get_settings

    monkeypatch.setenv(
        "SMS_ENABLED",
        "false",
    )

    get_settings.cache_clear()

    try:
        notification = (
            await create_pending_notification(
                db_session,
                suffix="disabled",
            )
        )

        result = await dispatch_sms_notification(
            db_session,
            notification=notification,
        )

        assert (
            result.status
            == SmsNotificationStatus.PENDING.value
        )

        assert result.attempt_count == 0
        assert result.provider_message_id is None
        assert result.sent_at is None

    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_dispatch_pending_batch(
    db_session,
):
    calls = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        calls.append(request)

        return httpx.Response(
            200,
            json={
                "success": True,
                "message": "SMS sent",
                "data": {
                    "status": "success",
                    "campaign_id":
                        str(900 + len(calls)),
                    "pages": 1,
                    "recipient_number":
                        "94771234567",
                    "sms_credit_balance":
                        "2499.00",
                    "charged_from": "main",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    first = await create_pending_notification(
        db_session,
        suffix="batch-1",
    )

    second = await create_pending_notification(
        db_session,
        suffix="batch-2",
    )

    results = (
        await dispatch_pending_sms_notifications(
            db_session,
            client=client,
            limit=10,
        )
    )

    ids = {
        row.id
        for row in results
    }

    assert first.id in ids
    assert second.id in ids

    rows = (
        await db_session.execute(
            select(SmsNotification).where(
                SmsNotification.id.in_(
                    [
                        first.id,
                        second.id,
                    ]
                )
            )
        )
    ).scalars().all()

    assert len(rows) == 2

    for row in rows:
        assert (
            row.status
            == SmsNotificationStatus.SENT.value
        )
        assert row.attempt_count == 1
        assert row.provider_message_id
        assert row.sent_at is not None


@pytest.mark.asyncio
async def test_non_pending_notification_not_resent(
    db_session,
):
    notification = (
        await create_pending_notification(
            db_session,
            suffix="already-sent",
        )
    )

    notification.status = (
        SmsNotificationStatus.SENT.value
    )
    notification.attempt_count = 1
    notification.provider_message_id = "existing"
    notification.sent_at = datetime.now()

    await db_session.flush()

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
    )

    assert (
        result.status
        == SmsNotificationStatus.SENT.value
    )

    assert result.attempt_count == 1
    assert result.provider_message_id == "existing"


def test_failed_sms_can_be_requeued():
    notification = SmsNotification(
        company_id=1,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone="+94771234567",
        event_type="retry_test",
        message="Retry test",
        status=(
            SmsNotificationStatus.FAILED.value
        ),
        deduplication_key=(
            "dispatcher-retry:eligible"
        ),
        attempt_count=1,
        last_error="Temporary provider error",
    )

    from app.services.sms import (
        retry_failed_sms_notification,
    )

    changed = retry_failed_sms_notification(
        notification
    )

    assert changed is True

    assert (
        notification.status
        == SmsNotificationStatus.PENDING.value
    )

    assert notification.attempt_count == 1
    assert notification.sent_at is None


def test_failed_sms_at_max_attempts_not_requeued():
    notification = SmsNotification(
        company_id=1,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone="+94771234567",
        event_type="retry_test",
        message="Retry max test",
        status=(
            SmsNotificationStatus.FAILED.value
        ),
        deduplication_key=(
            "dispatcher-retry:max"
        ),
        attempt_count=3,
        last_error="Provider failed",
    )

    from app.services.sms import (
        retry_failed_sms_notification,
    )

    changed = retry_failed_sms_notification(
        notification
    )

    assert changed is False

    assert (
        notification.status
        == SmsNotificationStatus.FAILED.value
    )

    assert notification.attempt_count == 3


def test_sent_sms_can_never_be_requeued():
    notification = SmsNotification(
        company_id=1,
        recipient_type=(
            SmsRecipientType.OWNER.value
        ),
        recipient_phone="+94771234567",
        event_type="retry_test",
        message="Already sent",
        status=(
            SmsNotificationStatus.SENT.value
        ),
        deduplication_key=(
            "dispatcher-retry:sent"
        ),
        attempt_count=1,
        provider_message_id="777",
        sent_at=datetime.now(),
    )

    from app.services.sms import (
        retry_failed_sms_notification,
    )

    changed = retry_failed_sms_notification(
        notification
    )

    assert changed is False

    assert (
        notification.status
        == SmsNotificationStatus.SENT.value
    )

    assert notification.attempt_count == 1
    assert notification.provider_message_id == "777"
    assert notification.sent_at is not None


@pytest.mark.asyncio
async def test_failed_sms_retry_then_success(
    db_session,
):
    calls = []

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        calls.append(request)

        return httpx.Response(
            200,
            json={
                "success": True,
                "message": "SMS sent",
                "data": {
                    "status": "success",
                    "campaign_id": "888",
                    "pages": 1,
                    "recipient_number":
                        "94771234567",
                    "sms_credit_balance":
                        "2498.00",
                    "charged_from": "main",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="retry-success",
        )
    )

    notification.status = (
        SmsNotificationStatus.FAILED.value
    )
    notification.attempt_count = 1
    notification.last_error = (
        "Temporary provider failure"
    )

    from app.services.sms import (
        retry_failed_sms_notification,
    )

    changed = retry_failed_sms_notification(
        notification
    )

    assert changed is True

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
        client=client,
    )

    assert len(calls) == 1

    assert (
        result.status
        == SmsNotificationStatus.SENT.value
    )

    assert result.attempt_count == 2
    assert result.provider_message_id == "888"
    assert result.last_error is None
    assert result.sent_at is not None


@pytest.mark.asyncio
async def test_atomic_claim_only_pending_row(
    db_session,
):
    from app.services.sms import (
        claim_sms_notification_for_processing,
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="atomic-claim",
        )
    )

    claimed = (
        await claim_sms_notification_for_processing(
            db_session,
            notification_id=notification.id,
        )
    )

    assert claimed is True

    await db_session.refresh(notification)

    assert (
        notification.status
        == SmsNotificationStatus.PROCESSING.value
    )

    assert notification.attempt_count == 1
    assert notification.processing_started_at is not None

    claimed_again = (
        await claim_sms_notification_for_processing(
            db_session,
            notification_id=notification.id,
        )
    )

    assert claimed_again is False

    await db_session.refresh(notification)

    assert notification.attempt_count == 1


@pytest.mark.asyncio
async def test_atomic_claim_rejects_sent_row(
    db_session,
):
    from app.services.sms import (
        claim_sms_notification_for_processing,
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="atomic-sent",
        )
    )

    notification.status = (
        SmsNotificationStatus.SENT.value
    )
    notification.attempt_count = 1
    notification.provider_message_id = "existing"
    notification.sent_at = datetime.now()

    await db_session.flush()

    claimed = (
        await claim_sms_notification_for_processing(
            db_session,
            notification_id=notification.id,
        )
    )

    assert claimed is False

    await db_session.refresh(notification)

    assert (
        notification.status
        == SmsNotificationStatus.SENT.value
    )
    assert notification.attempt_count == 1
    assert notification.provider_message_id == "existing"


@pytest.mark.asyncio
async def test_dispatch_clears_processing_lease_on_success(
    db_session,
):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "message": "SMS sent",
                "data": {
                    "status": "success",
                    "campaign_id": "atomic-777",
                    "pages": 1,
                    "recipient_number":
                        "94771234567",
                    "sms_credit_balance":
                        "2497.00",
                    "charged_from": "main",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="lease-success",
        )
    )

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
        client=client,
    )

    assert (
        result.status
        == SmsNotificationStatus.SENT.value
    )
    assert result.attempt_count == 1
    assert result.processing_started_at is None
    assert result.provider_message_id == "atomic-777"


@pytest.mark.asyncio
async def test_dispatch_clears_processing_lease_on_failure(
    db_session,
):
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": False,
                "message": "Atomic failure test",
                "data": {
                    "status": "failed",
                },
            },
        )

    client = SmslenzClient(
        base_url="https://www.smslenz.lk",
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            handler
        ),
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="lease-failure",
        )
    )

    result = await dispatch_sms_notification(
        db_session,
        notification=notification,
        client=client,
    )

    assert (
        result.status
        == SmsNotificationStatus.FAILED.value
    )
    assert result.attempt_count == 1
    assert result.processing_started_at is None
    assert result.sent_at is None


@pytest.mark.asyncio
async def test_stale_processing_becomes_failed_not_pending(
    db_session,
):
    from datetime import timedelta

    from app.services.sms import (
        recover_stale_processing_sms_notifications,
    )

    now = datetime(
        2026,
        8,
        14,
        20,
        0,
        0,
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="stale-processing",
        )
    )

    notification.status = (
        SmsNotificationStatus.PROCESSING.value
    )
    notification.attempt_count = 1
    notification.processing_started_at = (
        now - timedelta(minutes=10)
    )

    await db_session.commit()

    recovered = (
        await recover_stale_processing_sms_notifications(
            db_session,
            now=now,
            lease_seconds=300,
            commit_recovery=True,
        )
    )

    assert recovered == 1

    await db_session.refresh(notification)

    assert (
        notification.status
        == SmsNotificationStatus.FAILED.value
    )

    assert notification.attempt_count == 1

    assert (
        notification.processing_started_at
        is None
    )

    assert notification.sent_at is None

    assert (
        "delivery outcome unknown"
        in notification.last_error
    )

    assert (
        "manual retry required"
        in notification.last_error
    )


@pytest.mark.asyncio
async def test_fresh_processing_lease_is_not_recovered(
    db_session,
):
    from datetime import timedelta

    from app.services.sms import (
        recover_stale_processing_sms_notifications,
    )

    now = datetime(
        2026,
        8,
        14,
        20,
        0,
        0,
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="fresh-processing",
        )
    )

    notification.status = (
        SmsNotificationStatus.PROCESSING.value
    )
    notification.attempt_count = 1
    notification.processing_started_at = (
        now - timedelta(seconds=60)
    )

    await db_session.commit()

    recovered = (
        await recover_stale_processing_sms_notifications(
            db_session,
            now=now,
            lease_seconds=300,
            commit_recovery=True,
        )
    )

    assert recovered == 0

    await db_session.refresh(notification)

    assert (
        notification.status
        == SmsNotificationStatus.PROCESSING.value
    )

    assert (
        notification.processing_started_at
        is not None
    )


@pytest.mark.asyncio
async def test_sent_sms_is_never_stale_recovered(
    db_session,
):
    from datetime import timedelta

    from app.services.sms import (
        recover_stale_processing_sms_notifications,
    )

    now = datetime(
        2026,
        8,
        14,
        20,
        0,
        0,
    )

    notification = (
        await create_pending_notification(
            db_session,
            suffix="sent-stale-protection",
        )
    )

    notification.status = (
        SmsNotificationStatus.SENT.value
    )
    notification.attempt_count = 1
    notification.provider_message_id = (
        "already-sent-999"
    )
    notification.sent_at = (
        now - timedelta(minutes=20)
    )

    # Even if bad historical data left this timestamp set,
    # SENT status must protect the row.
    notification.processing_started_at = (
        now - timedelta(minutes=30)
    )

    await db_session.commit()

    recovered = (
        await recover_stale_processing_sms_notifications(
            db_session,
            now=now,
            lease_seconds=300,
            commit_recovery=True,
        )
    )

    assert recovered == 0

    await db_session.refresh(notification)

    assert (
        notification.status
        == SmsNotificationStatus.SENT.value
    )

    assert (
        notification.provider_message_id
        == "already-sent-999"
    )

    assert notification.sent_at is not None


@pytest.mark.asyncio
async def test_two_sessions_only_one_can_claim_same_sms(
    db_session,
):
    import asyncio

    from app.services.sms import (
        claim_sms_notification_for_processing,
    )

    # conftest already exposes the test session factory.
    from tests.conftest import TestSessionLocal

    notification = (
        await create_pending_notification(
            db_session,
            suffix="two-session-claim",
        )
    )

    notification_id = notification.id

    # Make the candidate visible to independent connections.
    await db_session.commit()

    async def claim_once():
        async with TestSessionLocal() as session:
            return (
                await claim_sms_notification_for_processing(
                    session,
                    notification_id=notification_id,
                    commit_claim=True,
                )
            )

    results = await asyncio.gather(
        claim_once(),
        claim_once(),
    )

    assert sorted(results) == [
        False,
        True,
    ]

    async with TestSessionLocal() as verify_session:
        row = await verify_session.get(
            SmsNotification,
            notification_id,
        )

        assert row is not None

        assert (
            row.status
            == SmsNotificationStatus.PROCESSING.value
        )

        assert row.attempt_count == 1

        assert (
            row.processing_started_at
            is not None
        )
