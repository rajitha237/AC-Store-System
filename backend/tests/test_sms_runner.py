import asyncio

import pytest

import app.services.sms_runner as sms_runner


class DisabledSmsSettings:
    sms_enabled = False
    sms_worker_interval_seconds = 60
    sms_dispatch_limit = 50


@pytest.mark.asyncio
async def test_sms_cycle_is_noop_when_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        sms_runner,
        "get_settings",
        lambda: DisabledSmsSettings(),
    )

    result = await sms_runner.run_sms_cycle()

    assert result.enabled is False
    assert result.companies_checked == 0
    assert result.owner_reminders_queued == 0
    assert result.installment_reminders_queued == 0
    assert result.notifications_dispatched == 0
    assert result.stale_rows_recovered == 0


@pytest.mark.asyncio
async def test_sms_worker_runs_and_cancels_cleanly(
    monkeypatch,
):
    cycle_started = asyncio.Event()
    calls = 0

    async def fake_run_sms_cycle():
        nonlocal calls

        calls += 1
        cycle_started.set()

        return sms_runner.SmsCycleResult(
            enabled=False
        )

    monkeypatch.setattr(
        sms_runner,
        "get_settings",
        lambda: DisabledSmsSettings(),
    )

    monkeypatch.setattr(
        sms_runner,
        "run_sms_cycle",
        fake_run_sms_cycle,
    )

    task = asyncio.create_task(
        sms_runner.sms_worker_loop()
    )

    await asyncio.wait_for(
        cycle_started.wait(),
        timeout=1.0,
    )

    task.cancel()

    with pytest.raises(
        asyncio.CancelledError
    ):
        await task

    assert calls == 1
