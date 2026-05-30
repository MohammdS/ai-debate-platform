# PRD - Watchdog

## Problem

Autonomous debate runs can hang if a provider call stalls, an IPC queue blocks, or a coroutine does not surface a failure. A stuck task should not freeze the full debate indefinitely.

## Requirement

The system needs a watchdog that:

- Runs monitored debate work with a timeout.
- Tracks heartbeat freshness.
- Cancels stale work.
- Restarts failed work with fresh services.
- Stops after a configured failure budget.

## Solution

`src/services/watchdog_agent.py` implements `WatchdogAgent`.

```python
watchdog = WatchdogAgent(max_failures=3, poll_interval=5.0)
watchdog.register("debate", fresh_debate_factory, timeout=600.0)
await watchdog.start()
```

## Behavior

- Wraps each registered coroutine in `asyncio.wait_for`.
- Records heartbeat timestamps through `beat(name)`.
- Cancels stale tasks and retries using the registered fresh factory.
- Rebuilds debaters, judge, orchestrator, channels, transcript, memory, and skill logs on retry.

## Configuration

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
- `src/cli/runner.py`
- `src/gui/debate_runner.py`
- `tests/unit/test_watchdog_agent.py`
