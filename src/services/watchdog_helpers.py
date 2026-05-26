from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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
