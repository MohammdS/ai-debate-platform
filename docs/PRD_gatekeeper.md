# PRD - API Gatekeeper

## Problem

The debate agents may share the same provider. Without coordination, concurrent calls can exceed provider rate limits, hang indefinitely, or hide transient failures.

## Requirement

All outbound LLM calls must pass through a central gatekeeper that:

- Enforces provider-specific requests-per-minute limits.
- Applies per-call timeouts.
- Retries transient failures with backoff.
- Tracks token usage and estimated cost.
- Logs structured call outcomes.

## Solution

`src/shared/gatekeeper.py` implements `ApiGatekeeper`.

```python
gatekeeper = ApiGatekeeper(provider="groq", model="llama-3.1-8b-instant")
result = await gatekeeper.execute(client.generate_response, messages)
```

## Behavior

- Loads RPM, timeout, retry count, and retry-after settings from `config/rate_limits.json`.
- Uses an `asyncio.Lock` and monotonic timestamp per provider to space outbound calls.
- Wraps each call in `asyncio.wait_for`.
- Retries failures up to the configured limit.
- Accumulates input tokens, output tokens, latency, errors, and estimated USD cost.

## Files

- `src/shared/gatekeeper.py`
- `src/shared/rate_config.py`
- `config/rate_limits.json`
- `config/pricing.json`
- `tests/unit/test_gatekeeper.py`
- `tests/unit/test_rate_config.py`
