from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentStatus(StrEnum):
    HEALTHY  = "HEALTHY"
    TIMEOUT  = "TIMEOUT"
    DEAD     = "DEAD"
    RESTARTED = "RESTARTED"
    STOPPED  = "STOPPED"


@dataclass
class AgentRecord:
    """Tracks the live state of one monitored agent coroutine."""
    name:     str
    factory:  Callable[[], Any]   # callable that returns a fresh coroutine
    timeout:  float
    task:     asyncio.Task | None = field(default=None, repr=False)
    status:   AgentStatus = AgentStatus.HEALTHY
    failures: int = 0


class WatchdogAgent:
    """
    Monitors a set of agent coroutines and recovers from failures.

    Responsibilities
    ----------------
    - Detect dead tasks (task.done() with exception).
    - Detect timeout (task runs longer than agent.timeout seconds).
    - Restart a failed agent if failures < max_failures.
    - Stop the entire system safely after max_failures per agent.
    - Log every state transition at the appropriate level.
    """

    def __init__(self, max_failures: int = 3,
                 poll_interval: float = 1.0,
                 logger: logging.Logger | None = None):
        self.max_failures  = max_failures
        self.poll_interval = poll_interval
        self._logger       = logger or logging.getLogger("watchdog")
        self._agents:   list[AgentRecord] = []
        self._stop_evt: asyncio.Event     = asyncio.Event()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, name: str, factory: Callable[[], Any],
                 timeout: float = 300.0) -> None:
        """
        Register an agent for monitoring.

        Args:
            name:    Human-readable agent name (used in logs).
            factory: Zero-argument callable that returns a fresh coroutine
                     each time it is called — used for restarts.
            timeout: Seconds before the agent is considered stuck.
        """
        self._agents.append(AgentRecord(name=name, factory=factory,
                                        timeout=timeout))
        self._logger.info("[watchdog] registered agent '%s' (timeout=%.0fs)", name, timeout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch all registered agents and begin monitoring."""
        for rec in self._agents:
            self._launch(rec)
        self._logger.info("[watchdog] monitoring %d agent(s)", len(self._agents))
        await self._monitor_loop()

    def stop(self) -> None:
        """Signal the watchdog to stop monitoring and cancel all tasks."""
        self._stop_evt.set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _launch(self, rec: AgentRecord) -> None:
        """Wrap the agent coroutine in a timeout task and start it."""
        async def _guarded():
            await asyncio.wait_for(rec.factory(), timeout=rec.timeout)

        rec.task   = asyncio.create_task(_guarded(), name=rec.name)
        rec.status = AgentStatus.HEALTHY
        self._logger.info("[watchdog] launched '%s'", rec.name)

    async def _monitor_loop(self) -> None:
        """Poll all agent tasks until stopped or all agents are done/stopped."""
        while not self._stop_evt.is_set():
            await asyncio.sleep(self.poll_interval)
            all_done = True

            for rec in self._agents:
                if rec.status == AgentStatus.STOPPED:
                    continue
                if rec.task is None or not rec.task.done():
                    all_done = False
                    continue

                exc = rec.task.exception() if not rec.task.cancelled() else None
                self._handle_done(rec, exc)
                if rec.status != AgentStatus.STOPPED:
                    all_done = False

            if all_done:
                self._logger.info("[watchdog] all agents finished — shutting down")
                break

    def _handle_done(self, rec: AgentRecord, exc: BaseException | None) -> None:
        """Decide whether to restart or stop an agent that has finished."""
        if exc is None and not rec.task.cancelled():
            # Clean exit
            rec.status = AgentStatus.STOPPED
            self._logger.info("[watchdog] '%s' completed cleanly", rec.name)
            return

        rec.failures += 1

        if isinstance(exc, asyncio.TimeoutError):
            rec.status = AgentStatus.TIMEOUT
            self._logger.error(
                "[watchdog] '%s' timed out (failure %d/%d)",
                rec.name, rec.failures, self.max_failures,
            )
        else:
            rec.status = AgentStatus.DEAD
            self._logger.error(
                "[watchdog] '%s' died with %s: %s (failure %d/%d)",
                rec.name, type(exc).__name__ if exc else "cancellation",
                exc, rec.failures, self.max_failures,
            )

        if rec.failures >= self.max_failures:
            rec.status = AgentStatus.STOPPED
            self._logger.critical(
                "[watchdog] '%s' exceeded max failures (%d) — stopping system",
                rec.name, self.max_failures,
            )
            self._stop_evt.set()
            self._cancel_all()
        else:
            self._restart(rec)

    def _restart(self, rec: AgentRecord) -> None:
        """Cancel the old task and launch a fresh coroutine."""
        if rec.task and not rec.task.done():
            rec.task.cancel()
        rec.status = AgentStatus.RESTARTED
        self._logger.warning(
            "[watchdog] restarting '%s' (attempt %d/%d)",
            rec.name, rec.failures, self.max_failures,
        )
        self._launch(rec)

    def _cancel_all(self) -> None:
        """Cancel every running task."""
        for rec in self._agents:
            if rec.task and not rec.task.done():
                rec.task.cancel()
                self._logger.warning("[watchdog] cancelled task '%s'", rec.name)
