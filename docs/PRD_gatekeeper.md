# PRD — API Gatekeeper

## Problem
All three agents share the same LLM provider. Without coordination, concurrent coroutines could hammer the API simultaneously, exceed rate limits, or fail silently on transient errors.

## Requirement
A centralized control layer that:
1. Enforces a configurable requests-per-minute (RPM) limit across all agents.
2. Adds per-call timeouts.
3. Retries failed calls with exponential backoff.

## Solution (`src/shared/gatekeeper.py`)

### Interface
```python
gatekeeper = ApiGatekeeper(rpm_limit=30, timeout=60.0)
result = await gatekeeper.execute(client.generate_response, messages)
```

### Rate Limiting
- `interval = 60 / rpm_limit` seconds between calls.
- `asyncio.Lock` ensures only one call proceeds at a time through the throttle gate.
- Lock is released **before** the API call — callers queue on the lock, not on each other's network latency.

### Timeout
- Each call wrapped in `asyncio.wait_for(..., timeout=self.timeout)`.
- `TimeoutError` is retried like any other exception.

### Retry Logic
- Up to the configured retry count; transient failures sleep with exponential backoff between attempts.
- Rate-limit failures use the configured `retry_after_seconds` before the next attempt.
- On final attempt, exception propagates to caller.

## Configuration (`config/rate_limits.json`)
```json
"default": {
  "rpm_limit": 30,
  "timeout_seconds": 60.0
}
```

## Files
- `src/shared/gatekeeper.py`
- `tests/unit/test_gatekeeper.py`
