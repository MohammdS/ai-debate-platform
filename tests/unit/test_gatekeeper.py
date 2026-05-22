import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.shared.gatekeeper import ApiGatekeeper

# --- helpers ---

def make_mock_client(return_value: str = "response") -> MagicMock:
    """Returns a mock SDK client whose generate_response is an AsyncMock."""
    client = MagicMock()
    client.generate_response = AsyncMock(return_value=return_value)
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
