import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sdk.exceptions import AIClientError, RateLimitError
from src.sdk.mock_client import MockAIClient
from src.shared.gatekeeper import ApiGatekeeper, _load_pricing


def make_mock_client(return_value: str = "response") -> MagicMock:
    """Returns a mock SDK client whose generate_response is an AsyncMock."""
    client = MagicMock()
    client.generate_response = AsyncMock(return_value=return_value)
    return client


def make_usage_client(prompt: int = 50, completion: int = 30) -> MockAIClient:
    """Real MockAIClient whose last_usage is pre-set for token assertions."""
    client = MockAIClient("mock-model", "fake-key")
    client.last_usage = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
    return client


# --- rate limiting ---

@pytest.mark.asyncio
async def test_rate_limit_enforces_interval():
    gk = ApiGatekeeper(rpm_limit=600)  # 0.1s interval
    client = make_mock_client()

    start = time.monotonic()
    await gk.execute(client.generate_response, [])
    await gk.execute(client.generate_response, [])
    assert time.monotonic() - start >= 0.05


# --- return value ---

@pytest.mark.asyncio
async def test_returns_mocked_response():
    gk = ApiGatekeeper(rpm_limit=1000)
    client = make_mock_client("hello from mock")

    result = await gk.execute(client.generate_response, [{"role": "user", "content": "hi"}])
    assert result == "hello from mock"
    client.generate_response.assert_awaited_once()


# --- retries ---

@pytest.mark.asyncio
async def test_retries_on_transient_error():
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=3)
    client = MagicMock()
    client.generate_response = AsyncMock(
        side_effect=[ValueError("transient"), ValueError("transient"), "ok"]
    )

    result = await gk.execute(client.generate_response, [])
    assert result == "ok"
    assert client.generate_response.await_count == 3


@pytest.mark.asyncio
async def test_raises_after_max_retries_exhausted():
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=2)
    client = MagicMock()
    client.generate_response = AsyncMock(side_effect=RuntimeError("permanent"))

    with pytest.raises(RuntimeError, match="permanent"):
        await gk.execute(client.generate_response, [])
    assert client.generate_response.await_count == 2


# --- timeout ---

@pytest.mark.asyncio
async def test_timeout_raises():
    gk = ApiGatekeeper(rpm_limit=1000, timeout=0.05, max_retries=1)
    client = MagicMock()

    async def slow(_):
        await asyncio.sleep(10)

    client.generate_response = slow
    with pytest.raises(asyncio.TimeoutError):
        await gk.execute(client.generate_response, [])


# --- logging ---

@pytest.mark.asyncio
async def test_logs_successful_call(caplog):
    gk = ApiGatekeeper(rpm_limit=1000)
    client = make_mock_client("logged")

    with caplog.at_level(logging.INFO, logger="gatekeeper"):
        await gk.execute(client.generate_response, [])

    assert any("starting" in r.message for r in caplog.records)
    assert any("succeeded" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_logs_failure(caplog):
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=1)
    client = MagicMock()
    client.generate_response = AsyncMock(side_effect=RuntimeError("boom"))

    with caplog.at_level(logging.WARNING, logger="gatekeeper"), pytest.raises(RuntimeError):
        await gk.execute(client.generate_response, [])

    assert any("failed" in r.message for r in caplog.records)


# --- config loading ---

def test_loads_limits_from_rate_limits_json():
    gk = ApiGatekeeper(provider="mock")
    assert gk.rpm_limit == 10000
    assert gk.timeout == 5.0
    assert gk.max_retries == 1


def test_explicit_params_override_config():
    gk = ApiGatekeeper(rpm_limit=5, timeout=99.0, max_retries=7, provider="mock")
    assert gk.rpm_limit == 5
    assert gk.timeout == 99.0
    assert gk.max_retries == 7


# --- stats ---

@pytest.mark.asyncio
async def test_get_stats_returns_expected_keys():
    gk = ApiGatekeeper(rpm_limit=1000)
    stats = gk.get_stats()
    assert "total_calls" in stats
    assert "total_latency_ms" in stats
    assert "total_errors" in stats


@pytest.mark.asyncio
async def test_stats_after_successful_call():
    gk = ApiGatekeeper(rpm_limit=1000)
    client = make_mock_client("ok")
    await gk.execute(client.generate_response, [])
    stats = gk.get_stats()
    assert stats["total_calls"] == 1
    assert stats["total_errors"] == 0
    assert stats["total_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_stats_after_failed_call():
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=1)
    client = MagicMock()
    client.generate_response = AsyncMock(side_effect=RuntimeError("err"))
    with pytest.raises(RuntimeError):
        await gk.execute(client.generate_response, [])
    stats = gk.get_stats()
    assert stats["total_errors"] == 1


# --- fallback client ---

@pytest.mark.asyncio
async def test_fallback_client_used_on_ai_client_error():
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=1)
    primary = MagicMock()
    primary.generate_response = AsyncMock(side_effect=AIClientError("primary failed"))
    fallback = make_mock_client("fallback response")

    result = await gk.execute(primary.generate_response, [], fallback_client=fallback)
    assert result == "fallback response"


# --- RateLimitError retry ---

@pytest.mark.asyncio
async def test_rate_limit_error_triggers_retry_after_wait():
    gk = ApiGatekeeper(rpm_limit=1000, max_retries=2)
    gk._retry_after = 0.01  # speed up test
    client = MagicMock()
    client.generate_response = AsyncMock(
        side_effect=[RateLimitError("429"), "success after wait"]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await gk.execute(client.generate_response, [])

    assert result == "success after wait"
    mock_sleep.assert_called()


# ---------------------------------------------------------------------------
# Token tracking and cost estimation
# ---------------------------------------------------------------------------

def test_get_stats_includes_token_and_cost_keys():
    gk = ApiGatekeeper(rpm_limit=1000)
    stats = gk.get_stats()
    assert "total_tokens_in"    in stats
    assert "total_tokens_out"   in stats
    assert "estimated_cost_usd" in stats


@pytest.mark.asyncio
async def test_tokens_read_from_last_usage():
    gk = ApiGatekeeper(rpm_limit=1000, provider="mock", model="default")
    client = make_usage_client(prompt=100, completion=50)

    await gk.execute(client.generate_response, [{"role": "user", "content": "hi"}])

    stats = gk.get_stats()
    assert stats["total_tokens_in"]  == 100
    assert stats["total_tokens_out"] == 50


@pytest.mark.asyncio
async def test_tokens_accumulate_across_calls():
    gk = ApiGatekeeper(rpm_limit=1000, provider="mock", model="default")
    client = make_usage_client(prompt=40, completion=20)

    await gk.execute(client.generate_response, [{"role": "user", "content": "a"}])
    await gk.execute(client.generate_response, [{"role": "user", "content": "b"}])

    stats = gk.get_stats()
    assert stats["total_tokens_in"]  == 80
    assert stats["total_tokens_out"] == 40


@pytest.mark.asyncio
async def test_cost_zero_for_mock_provider():
    gk = ApiGatekeeper(rpm_limit=1000, provider="mock", model="default")
    client = make_usage_client(prompt=1000, completion=500)

    await gk.execute(client.generate_response, [{"role": "user", "content": "x"}])

    assert gk.get_stats()["estimated_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_cost_zero_for_openrouter_free_model_but_tokens_counted():
    gk = ApiGatekeeper(
        rpm_limit=1000,
        provider="openrouter",
        model="openai/gpt-oss-120b:free",
    )
    client = make_usage_client(prompt=1000, completion=500)

    await gk.execute(client.generate_response, [{"role": "user", "content": "x"}])

    stats = gk.get_stats()
    assert stats["total_tokens_in"] == 1000
    assert stats["total_tokens_out"] == 500
    assert stats["estimated_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_cost_calculated_from_pricing():
    # groq llama-3.1-8b-instant: $0.05/1M in, $0.08/1M out
    gk = ApiGatekeeper(rpm_limit=1000, provider="groq", model="llama-3.1-8b-instant")
    client = make_usage_client(prompt=1_000_000, completion=1_000_000)

    await gk.execute(client.generate_response, [{"role": "user", "content": "x"}])

    stats = gk.get_stats()
    assert abs(stats["estimated_cost_usd"] - 0.13) < 0.001  # 0.05 + 0.08


@pytest.mark.asyncio
async def test_tokens_zero_when_client_has_no_last_usage():
    gk = ApiGatekeeper(rpm_limit=1000)
    client = make_mock_client("no usage")   # MagicMock — no last_usage

    await gk.execute(client.generate_response, [])

    stats = gk.get_stats()
    assert stats["total_tokens_in"]  == 0
    assert stats["total_tokens_out"] == 0


@pytest.mark.asyncio
async def test_structured_log_includes_token_fields(caplog):
    gk = ApiGatekeeper(rpm_limit=1000, provider="mock", model="default")
    client = make_usage_client(prompt=20, completion=10)

    with caplog.at_level(logging.DEBUG, logger="gatekeeper"):
        await gk.execute(client.generate_response, [{"role": "user", "content": "x"}])

    json_logs = [r.message for r in caplog.records if "tokens_in" in r.message]
    assert len(json_logs) >= 1
    import json
    record = json.loads(json_logs[0])
    assert record["tokens_in"]  == 20
    assert record["tokens_out"] == 10
    assert "cost_usd" in record


def test_load_pricing_known_model():
    in_rate, out_rate = _load_pricing("groq", "llama-3.1-8b-instant")
    assert in_rate  == pytest.approx(0.05)
    assert out_rate == pytest.approx(0.08)


def test_load_pricing_unknown_model_uses_provider_default():
    in_rate, out_rate = _load_pricing("groq", "some-unknown-model")
    assert in_rate > 0


def test_load_pricing_unknown_provider_uses_global_default():
    in_rate, out_rate = _load_pricing("unknown_provider", "unknown_model")
    assert in_rate  == pytest.approx(0.10)
    assert out_rate == pytest.approx(0.10)


# --- provider lock (new-loop path) ---

@pytest.mark.asyncio
async def test_provider_lock_recreated_for_new_event_loop():
    """
    _get_provider_lock must return a lock bound to the *current* event loop.
    When two tests run with separate loops the lock must be recreated, not reused.
    """
    provider = "_test_loop_isolation_provider_"
    # Clear any stale state from a previous test run
    ApiGatekeeper._provider_locks.pop(provider, None)
    ApiGatekeeper._provider_loops.pop(provider, None)

    lock1 = ApiGatekeeper._get_provider_lock(provider)
    assert isinstance(lock1, asyncio.Lock)

    # Simulate a different event loop by manually overriding the stored loop
    ApiGatekeeper._provider_loops[provider] = None  # pretend old loop was None

    lock2 = ApiGatekeeper._get_provider_lock(provider)
    # Must have been recreated since the stored loop no longer matches
    assert lock2 is not lock1
