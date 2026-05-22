import asyncio
import logging

import pytest

from src.services.watchdog_agent import AgentStatus, WatchdogAgent

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def make_watchdog(max_failures: int = 3, poll: float = 0.05) -> WatchdogAgent:
    return WatchdogAgent(max_failures=max_failures, poll_interval=poll)


async def healthy_agent():
    """Completes immediately."""


async def slow_agent():
    """Simulates a stuck process."""
    await asyncio.sleep(9999)


async def failing_agent():
    """Always raises."""
    raise RuntimeError("agent crashed")


# ------------------------------------------------------------------
# clean completion
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_healthy_agent_completes():
    wd = make_watchdog()
    wd.register("ok", healthy_agent, timeout=5.0)
    await wd.start()
    assert wd._agents[0].status == AgentStatus.STOPPED
    assert wd._agents[0].failures == 0


# ------------------------------------------------------------------
# dead process detection
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_detects_dead_agent_and_restarts():
    wd = make_watchdog(max_failures=3)
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("crash")

    wd.register("flaky", flaky, timeout=5.0)
    await wd.start()

    assert calls["n"] == 3
    assert wd._agents[0].status == AgentStatus.STOPPED
    assert wd._agents[0].failures == 2


@pytest.mark.asyncio
async def test_dead_agent_status_recorded():
    wd = make_watchdog(max_failures=1)
    wd.register("dead", failing_agent, timeout=5.0)
    await wd.start()

    rec = wd._agents[0]
    assert rec.status == AgentStatus.STOPPED
    assert rec.failures == 1


# ------------------------------------------------------------------
# timeout detection
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_detects_timeout():
    wd = make_watchdog(max_failures=1)
    wd.register("slow", slow_agent, timeout=0.05)
    await wd.start()

    rec = wd._agents[0]
    assert rec.failures >= 1
    assert rec.status == AgentStatus.STOPPED


# ------------------------------------------------------------------
# max failures → system stop
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stops_system_after_max_failures():
    wd = make_watchdog(max_failures=2)
    wd.register("bad", failing_agent, timeout=5.0)
    await wd.start()

    assert wd._stop_evt.is_set()
    assert wd._agents[0].failures == 2
    assert wd._agents[0].status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_cancels_other_agents_on_max_failures():
    wd = make_watchdog(max_failures=1, poll=0.05)

    async def slow():
        await asyncio.sleep(9999)

    wd.register("bad",  failing_agent, timeout=5.0)
    wd.register("slow", slow,          timeout=60.0)
    await wd.start()

    assert wd._stop_evt.is_set()
    # Give the event loop a tick to finish processing cancellations
    await asyncio.sleep(0.05)
    slow_rec = wd._agents[1]
    assert slow_rec.task.cancelled() or slow_rec.task.done() or slow_rec.task.cancelling() > 0


# ------------------------------------------------------------------
# logging
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logs_failure(caplog):
    wd = make_watchdog(max_failures=1)
    wd.register("bad", failing_agent, timeout=5.0)

    with caplog.at_level(logging.ERROR, logger="watchdog"):
        await wd.start()

    assert any("died" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_logs_critical_on_system_stop(caplog):
    wd = make_watchdog(max_failures=1)
    wd.register("bad", failing_agent, timeout=5.0)

    with caplog.at_level(logging.CRITICAL, logger="watchdog"):
        await wd.start()

    assert any("exceeded max failures" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_logs_restart(caplog):
    wd = make_watchdog(max_failures=3)
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("once")

    wd.register("flaky", flaky, timeout=5.0)

    with caplog.at_level(logging.WARNING, logger="watchdog"):
        await wd.start()

    assert any("restarting" in r.message for r in caplog.records)


# ------------------------------------------------------------------
# manual stop
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_stop_halts_monitoring():
    wd = make_watchdog(poll=0.05)

    async def forever():
        await asyncio.sleep(9999)

    wd.register("forever", forever, timeout=60.0)

    monitor = asyncio.create_task(wd.start())
    await asyncio.sleep(0.1)
    wd.stop()
    await monitor

    assert wd._stop_evt.is_set()
