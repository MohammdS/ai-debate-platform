# PRD — Watchdog

## Problem
Autonomous agent runs can hang indefinitely if an LLM API stalls, a queue blocks, or a network timeout isn't surfaced correctly. A single stuck coroutine freezes the entire debate.

## Requirement
The lecture engineering requirements state: *"Watchdog with keep-alive — mandatory in every autonomous agents project. If a process falls, kill it and restart it."*

## Solution (`src/shared/watchdog.py`) — Pending Implementation

### Interface
```python
watchdog = Watchdog(timeout=600.0, max_retries=3, logger=logger)
verdict = await watchdog.run(orchestrator.run_debate)
```

### Behaviour
- Wraps the entire `run_debate()` coroutine in `asyncio.wait_for(..., timeout)`.
- On `TimeoutError`: logs error, resets orchestrator state, retries up to `max_retries`.
- On unrecoverable failure (max retries exceeded): re-raises for the caller to handle.
- On success: returns the verdict string.

### Retry Reset
Each retry must reset `judge.transcript` and `orchestrator.history` to `[]`, and re-wire IPC channels (channels are single-use once a coroutine exits).

## Configuration (`config/setup.json`)
```json
"watchdog": {
  "timeout_seconds": 600.0,
  "max_retries": 3
}
```

## Files
- `src/shared/watchdog.py` — **not yet implemented**
- `tests/unit/test_watchdog.py` — **not yet implemented**

## Status
**Pending.** Tracked in `docs/TODO.md`.
