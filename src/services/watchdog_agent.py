from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.ipc.heartbeat import HeartbeatMonitor


class AgentStatus(StrEnum):
    HEALTHY   = "HEALTHY"
    TIMEOUT   = "TIMEOUT"
    DEAD      = "DEAD"
    RESTARTED = "RESTARTED"
    STOPPED   = "STOPPED"


@dataclass
class AgentRecord:
    """Live state of one monitored agent coroutine."""
    name:     str
    factory:  Callable[[], Any]
    timeout:  float
    task:     asyncio.Task | None = field(default=None, repr=False)
    status:   AgentStatus = AgentStatus.HEALTHY
    failures: int = 0
    # Set to True when a stale-heartbeat restart has been requested but not
    # yet processed by _handle_done, so we don't cancel the task repeatedly.
    stale_restart_triggered: bool = False


class WatchdogAgent:
    """
    Monitors agent coroutines; detects failures, timeouts, and heartbeat
    staleness; restarts failed agents with backoff up to *max_failures*.
    """

    def __init__(self, max_failures: int = 3,
                 poll_interval: float = 1.0,
                 heartbeat_threshold: float = 60.0,
                 backoff_base: float = 0.5,
                 logger: logging.Logger | None = None):
        self.max_failures  = max_failures
        self.poll_interval = poll_interval
        self.backoff_base  = backoff_base
        self._logger       = logger or logging.getLogger("watchdog")
        self._agents:    list[AgentRecord]  = []
        self._stop_evt:  asyncio.Event      = asyncio.Event()
        self._heartbeat: HeartbeatMonitor   = HeartbeatMonitor(heartbeat_threshold)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, name: str, factory: Callable[[], Any],
                 timeout: float = 300.0) -> None:
        """Register an agent. *factory* must return a fresh coroutine each call."""
        self._agents.append(AgentRecord(name=name, factory=factory, timeout=timeout))
        self._heartbeat.register(name)
        self._log_event("registered", name, AgentStatus.HEALTHY, timeout=timeout)

    def beat(self, name: str) -> None:
        """Called by an agent to signal it is alive and making progress."""
        self._heartbeat.beat(name)

    async def start(self) -> None:
        """Launch all registered agents and begin monitoring."""
        for rec in self._agents:
            self._launch(rec)
        self._log_event("started", "watchdog", AgentStatus.HEALTHY,
                        agent_count=len(self._agents))
        await self._monitor_loop()

    def stop(self) -> None:
        """Signal watchdog to stop and cancel all tasks."""
        self._stop_evt.set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _launch(self, rec: AgentRecord) -> None:
        async def _guarded():
            await asyncio.wait_for(rec.factory(), timeout=rec.timeout)
        rec.task                    = asyncio.create_task(_guarded(), name=rec.name)
        rec.status                  = AgentStatus.HEALTHY
        rec.stale_restart_triggered = False
        self._heartbeat.beat(rec.name)
        self._log_event("launched", rec.name, AgentStatus.HEALTHY)

    async def _monitor_loop(self) -> None:
        while not self._stop_evt.is_set():
            await asyncio.sleep(self.poll_interval)
            all_done = True

            for rec in self._agents:
                if rec.status == AgentStatus.STOPPED:
                    continue
                if rec.task is None or not rec.task.done():
                    all_done = False
                    self._check_heartbeat(rec)
                    continue
                exc = rec.task.exception() if not rec.task.cancelled() else None
                self._handle_done(rec, exc)
                if rec.status != AgentStatus.STOPPED:
                    all_done = False

            if all_done:
                self._log_event("all_done", "watchdog", AgentStatus.STOPPED)
                break

    def _check_heartbeat(self, rec: AgentRecord) -> None:
        if not self._heartbeat.is_alive(rec.name):
            ago = self._heartbeat.last_beat_ago(rec.name) or 0.0
            self._log_event("heartbeat_stale", rec.name, rec.status, idle_secs=ago)
            if not rec.stale_restart_triggered and rec.task and not rec.task.done():
                rec.stale_restart_triggered = True
                self._log_event("heartbeat_cancel", rec.name, rec.status, idle_secs=ago)
                rec.task.cancel()

    def _handle_done(self, rec: AgentRecord, exc: BaseException | None) -> None:
        if exc is None and not rec.task.cancelled():
            rec.status = AgentStatus.STOPPED
            self._log_event("completed", rec.name, AgentStatus.STOPPED)
            return

        rec.failures += 1
        if isinstance(exc, asyncio.TimeoutError):
            rec.status = AgentStatus.TIMEOUT
            self._log_event("timeout", rec.name, AgentStatus.TIMEOUT,
                            failure=rec.failures, max=self.max_failures)
        else:
            rec.status = AgentStatus.DEAD
            self._log_event("dead", rec.name, AgentStatus.DEAD,
                            error=str(exc) if exc else "cancelled",
                            failure=rec.failures, max=self.max_failures)

        if rec.failures >= self.max_failures:
            rec.status = AgentStatus.STOPPED
            self._log_event("max_failures", rec.name, AgentStatus.STOPPED,
                            failure=rec.failures)
            self._stop_evt.set()
            self._cancel_all()
        else:
            self._restart(rec)

    def _restart(self, rec: AgentRecord) -> None:
        if rec.task and not rec.task.done():
            rec.task.cancel()
        rec.task   = None   # prevent monitor re-processing until _launch fires
        rec.status = AgentStatus.RESTARTED
        backoff = self.backoff_base * rec.failures
        self._log_event("restarting", rec.name, AgentStatus.RESTARTED,
                        attempt=rec.failures, backoff_secs=backoff)
        asyncio.get_event_loop().call_later(backoff, self._launch, rec)

    def _cancel_all(self) -> None:
        for rec in self._agents:
            if rec.task and not rec.task.done():
                rec.task.cancel()
                self._log_event("cancelled", rec.name, rec.status)

    def _log_event(self, event: str, agent: str,
                   status: AgentStatus, **extra: Any) -> None:
        record = {"ts": time.time(), "event": event,
                  "agent": agent, "status": str(status), **extra}
        level = (logging.CRITICAL if event == "max_failures"
                 else logging.ERROR   if event in ("dead", "timeout")
                 else logging.WARNING if event in ("restarting", "heartbeat_stale", "heartbeat_cancel")
                 else logging.INFO)
        self._logger.log(level, "[watchdog] %s", json.dumps(record))
