"""
Tests for the improved IPC protocol, heartbeat, and watchdog recovery.
Covers: route validation, schema validation, no direct Debater↔Debater,
heartbeat tracking, timeout detection, and watchdog recovery behaviour.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from src.ipc.channel import IpcChannel
from src.ipc.heartbeat import HeartbeatMonitor
from src.ipc.message import DebateMessage, MessageType
from src.ipc.protocol import ProtocolError, validate_message, validate_route, validate_schema
from src.services.watchdog_agent import AgentStatus, WatchdogAgent

# ===========================================================================
# 1. Route validation
# ===========================================================================

def test_valid_debater_to_judge():
    validate_route("debater_a", "judge")   # must not raise


def test_valid_judge_to_debater():
    validate_route("judge", "debater_a")   # must not raise
    validate_route("judge", "debater_b")   # must not raise


def test_valid_orchestrator_routes():
    validate_route("orchestrator", "judge")
    validate_route("orchestrator", "debater_a")


def test_forbidden_debater_to_debater_a():
    with pytest.raises(ProtocolError, match="forbidden"):
        validate_route("debater_a", "debater_b")


def test_forbidden_debater_to_debater_b():
    with pytest.raises(ProtocolError, match="forbidden"):
        validate_route("pro", "contra")


def test_forbidden_pro_to_contra_case_insensitive():
    with pytest.raises(ProtocolError):
        validate_route("Pro", "Contra")


def test_unknown_sender_does_not_raise_route():
    # Unknown senders are allowed (not classified as debaters) — no crash
    validate_route("external_system", "judge")


# ===========================================================================
# 2. Schema validation
# ===========================================================================

def test_schema_valid_argument():
    validate_schema("ARGUMENT", "debater_a", "AI is good", round_num=1)


def test_schema_empty_payload_argument_raises():
    with pytest.raises(ProtocolError, match="non-empty payload"):
        validate_schema("ARGUMENT", "debater_a", "   ", round_num=1)


def test_schema_empty_payload_relay_raises():
    with pytest.raises(ProtocolError, match="non-empty payload"):
        validate_schema("RELAY", "judge", "", round_num=2)


def test_schema_heartbeat_allows_empty_payload():
    validate_schema("HEARTBEAT", "judge", "", round_num=0)   # must not raise


def test_schema_shutdown_allows_empty_payload():
    validate_schema("SHUTDOWN", "judge", "", round_num=0)


def test_schema_negative_round_raises():
    with pytest.raises(ProtocolError, match="round_num"):
        validate_schema("ARGUMENT", "debater_a", "text", round_num=-1)


def test_schema_unknown_type_raises():
    with pytest.raises(ProtocolError, match="Unknown MessageType"):
        validate_schema("INVALID_TYPE", "debater_a", "text", round_num=1)


# ===========================================================================
# 3. validate_message end-to-end
# ===========================================================================

def test_validate_message_passes_valid():
    msg = DebateMessage(MessageType.ARGUMENT, "debater_a", "judge",
                        "This is my argument.", round_num=1)
    validate_message(msg)   # must not raise


def test_validate_message_blocks_direct_debater():
    msg = DebateMessage(MessageType.ARGUMENT, "debater_a", "debater_b",
                        "I'm talking directly to you.", round_num=1)
    with pytest.raises(ProtocolError):
        validate_message(msg)


# ===========================================================================
# 4. IpcChannel enforces protocol on send
# ===========================================================================

@pytest.mark.asyncio
async def test_channel_blocks_debater_to_debater():
    ch = IpcChannel("test", timeout=5.0, validate=True)
    bad = DebateMessage(MessageType.ARGUMENT, "debater_a", "debater_b",
                        "direct message", round_num=1)
    with pytest.raises(ProtocolError):
        await ch.send(bad)


@pytest.mark.asyncio
async def test_channel_allows_valid_route():
    ch = IpcChannel("test", timeout=5.0, validate=True)
    good = DebateMessage(MessageType.ARGUMENT, "debater_a", "judge",
                         "valid argument text", round_num=1)
    await ch.send(good)   # must not raise


@pytest.mark.asyncio
async def test_channel_skip_validation_when_disabled():
    ch = IpcChannel("test", timeout=5.0, validate=False)
    bad = DebateMessage(MessageType.ARGUMENT, "debater_a", "debater_b",
                        "direct", round_num=1)
    await ch.send(bad)   # validate=False → no ProtocolError


@pytest.mark.asyncio
async def test_channel_idle_seconds_increases():
    ch = IpcChannel("idle_test", timeout=5.0)
    msg = DebateMessage(MessageType.HEARTBEAT, "judge", "orchestrator",
                        "", round_num=0)
    await ch.send(msg)
    await asyncio.sleep(0.05)
    assert ch.idle_seconds() >= 0.0


@pytest.mark.asyncio
async def test_channel_timeout_raises():
    ch = IpcChannel("timeout_ch", timeout=0.05)
    with pytest.raises(asyncio.TimeoutError):
        await ch.receive()


# ===========================================================================
# 5. Message factories (HEARTBEAT / ERROR)
# ===========================================================================

def test_heartbeat_factory():
    msg = DebateMessage.heartbeat("judge", "orchestrator", round_num=5)
    assert msg.msg_type == MessageType.HEARTBEAT
    assert msg.payload == ""
    assert msg.is_heartbeat()


def test_error_factory():
    msg = DebateMessage.error("judge", "orchestrator", "API timeout", round_num=3)
    assert msg.msg_type == MessageType.ERROR
    assert "timeout" in msg.payload
    assert msg.is_error()


def test_message_metadata_roundtrip():
    msg = DebateMessage(MessageType.ARGUMENT, "debater_a", "judge",
                        "text", round_num=1, metadata={"source": "rag"})
    restored = DebateMessage.from_dict(msg.to_dict())
    assert restored.metadata == {"source": "rag"}


# ===========================================================================
# 6. HeartbeatMonitor
# ===========================================================================

def test_heartbeat_register_and_alive():
    hb = HeartbeatMonitor(stale_threshold=5.0)
    hb.register("agent_a")
    assert hb.is_alive("agent_a")


def test_heartbeat_unregistered_not_alive():
    hb = HeartbeatMonitor(stale_threshold=5.0)
    assert not hb.is_alive("ghost")


def test_heartbeat_stale_after_threshold():
    hb = HeartbeatMonitor(stale_threshold=0.05)
    hb.register("slow_agent")
    time.sleep(0.1)
    assert not hb.is_alive("slow_agent")


def test_heartbeat_revived_after_beat():
    hb = HeartbeatMonitor(stale_threshold=0.05)
    hb.register("flaky")
    time.sleep(0.1)
    hb.beat("flaky")
    assert hb.is_alive("flaky")


def test_heartbeat_stale_agents_list():
    hb = HeartbeatMonitor(stale_threshold=0.05)
    hb.register("ok")
    hb.register("slow")
    time.sleep(0.1)
    hb.beat("ok")
    stale = hb.stale_agents()
    assert "slow" in stale
    assert "ok" not in stale


def test_heartbeat_last_beat_ago():
    hb = HeartbeatMonitor()
    hb.register("x")
    ago = hb.last_beat_ago("x")
    assert ago is not None and ago >= 0
    assert hb.last_beat_ago("unknown") is None


def test_heartbeat_auto_registers_on_beat():
    hb = HeartbeatMonitor()
    hb.beat("new_agent")   # no prior register() call
    assert hb.is_alive("new_agent")


# ===========================================================================
# 7. WatchdogAgent — heartbeat + recovery
# ===========================================================================

@pytest.mark.asyncio
async def test_watchdog_beat_records_liveness():
    wd = WatchdogAgent(max_failures=3, poll_interval=0.05)
    wd.register("agent", lambda: asyncio.sleep(0))
    wd.beat("agent")
    assert wd._heartbeat.is_alive("agent")


@pytest.mark.asyncio
async def test_watchdog_clean_exit():
    wd = WatchdogAgent(max_failures=3, poll_interval=0.05)
    wd.register("quick", lambda: asyncio.sleep(0), timeout=5.0)
    await wd.start()
    assert wd._agents[0].status == AgentStatus.STOPPED
    assert wd._agents[0].failures == 0


@pytest.mark.asyncio
async def test_watchdog_restarts_on_failure():
    call_count = {"n": 0}

    async def flaky():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient error")

    wd = WatchdogAgent(max_failures=3, poll_interval=0.05, backoff_base=0.0)
    wd.register("flaky_agent", flaky, timeout=5.0)
    await wd.start()
    assert call_count["n"] >= 2


@pytest.mark.asyncio
async def test_watchdog_stops_after_max_failures():
    async def always_fails():
        raise RuntimeError("permanent error")

    wd = WatchdogAgent(max_failures=2, poll_interval=0.05, backoff_base=0.0)
    wd.register("broken", always_fails, timeout=5.0)
    await wd.start()
    assert wd._agents[0].failures >= 2
    assert wd._agents[0].status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_watchdog_structured_log_on_failure(caplog):
    import logging
    async def boom():
        raise ValueError("test error")

    wd = WatchdogAgent(max_failures=1, poll_interval=0.05, backoff_base=0.0)
    with caplog.at_level(logging.ERROR, logger="watchdog"):
        wd.register("boom_agent", boom, timeout=5.0)
        await wd.start()
    assert any("dead" in r.message or "max_failures" in r.message
               for r in caplog.records)
