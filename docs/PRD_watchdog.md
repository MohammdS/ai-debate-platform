# PRD — Watchdog

## Problem
Autonomous agent runs can hang indefinitely if an LLM API stalls, a queue blocks, or a network timeout isn't surfaced correctly. A single stuck coroutine freezes the entire debate.

## Requirement
The lecture engineering requirements state: *"Watchdog with keep-alive — mandatory in every autonomous agents project. If a process falls, kill it and restart it."*

## Solution (`src/services/watchdog_agent.py`) — Implemented

### Interface
```python
watchdog = WatchdogAgent(max_failures=3, poll_interval=1.0)
watchdog.register("debate", fresh_debate_factory, timeout=600.0)
await watchdog.start()
```

### Behaviour
- Wraps registered agent/debate coroutines in `asyncio.wait_for(..., timeout)`.
- Tracks heartbeat staleness and cancels stale tasks.
- Restarts failed/stale runs with backoff until `max_failures`.
- Stops the monitored system when the failure budget is exhausted.

### Retry Reset
CLI and non-stream GUI registrations use fresh factories, so each retry creates new debaters, judge, orchestrator, IPC channels, transcript, memory, and skill logs.

## Configuration (`config/setup.json`)
```json
"watchdog": {
  "timeout_seconds": 600.0,
  "max_failures": 3,
  "poll_interval_seconds": 5.0
}
```

## Files
- `src/services/watchdog_agent.py`
- `src/services/watchdog_helpers.py`
- `tests/unit/test_watchdog_agent.py`

## Status
**Implemented.** Tracked by `tests/unit/test_watchdog_agent.py`.
