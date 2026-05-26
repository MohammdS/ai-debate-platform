"""Liveness tracking for named agents via periodic beat() calls."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class _AgentBeat:
    name: str
    last_beat: float = field(default_factory=time.monotonic)
    beat_count: int = 0


class HeartbeatMonitor:
    """
    Tracks liveness of named agents.

    Agents call beat(name) periodically. is_alive() / stale_agents()
    tell the watchdog whether an agent has gone silent.
    """

    def __init__(self, stale_threshold: float = 30.0) -> None:
        self.stale_threshold = stale_threshold
        self._agents: dict[str, _AgentBeat] = {}

    def register(self, name: str) -> None:
        """Initialise the beat record for *name* (resets if already present)."""
        self._agents[name] = _AgentBeat(name=name)
        logger.debug("[heartbeat] registered '%s'", name)

    def beat(self, name: str) -> None:
        """Record a liveness signal from *name*."""
        if name not in self._agents:
            self.register(name)
        rec = self._agents[name]
        rec.last_beat = time.monotonic()
        rec.beat_count += 1
        logger.debug("[heartbeat] beat '%s' (#%d)", name, rec.beat_count)

    def is_alive(self, name: str, threshold: float | None = None) -> bool:
        """Return True if *name* beat within *threshold* seconds."""
        rec = self._agents.get(name)
        if rec is None:
            return False
        limit = threshold if threshold is not None else self.stale_threshold
        return time.monotonic() - rec.last_beat < limit

    def stale_agents(self, threshold: float | None = None) -> list[str]:
        """Return names of agents that have not beaten within the threshold."""
        return [n for n in self._agents if not self.is_alive(n, threshold)]

    def last_beat_ago(self, name: str) -> float | None:
        """Seconds since the last beat for *name*, or None if unregistered."""
        rec = self._agents.get(name)
        return None if rec is None else time.monotonic() - rec.last_beat

    def registered(self) -> list[str]:
        return list(self._agents.keys())
