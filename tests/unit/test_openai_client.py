"""Tests for OpenAIClient — happy path, JSON error, rate limit, HTTP error."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sdk.exceptions import InvalidResponseError, ProviderHTTPError, RateLimitError
from src.sdk.openai_client import OpenAIClient


def _make_client() -> OpenAIClient:
    return OpenAIClient("gpt-4", "test-key")


def _mock_response(status: int, body: dict | str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.is_success = (200 <= status < 300)
    if isinstance(body, dict):
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        resp.text = body
    return resp


@pytest.mark.asyncio
async def test_openai_client_attributes():
    client = _make_client()
    assert client.model_name == "gpt-4"
    assert client.api_key == "test-key"


@pytest.mark.asyncio
async def test_openai_success_returns_content():
    client = _make_client()
    body = {
        "choices": [{"message": {"content": "Hello from OpenAI"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    resp = _mock_response(200, body)

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        result = await client.generate_response([{"role": "user", "content": "hi"}])

    assert result == "Hello from OpenAI"
    assert client.last_usage["prompt_tokens"] == 10
    assert client.last_usage["completion_tokens"] == 5


@pytest.mark.asyncio
async def test_openai_rate_limit_raises():
    client = _make_client()
    resp = _mock_response(429, "rate limited")
    resp.text = "rate limited"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        with pytest.raises(RateLimitError):
            await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_openai_http_error_raises():
    client = _make_client()
    resp = _mock_response(500, "server error")
    resp.text = "server error"

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        with pytest.raises(ProviderHTTPError):
            await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_openai_json_decode_error_raises_invalid_response():
    client = _make_client()
    resp = _mock_response(200, "<html>not json</html>")  # triggers JSONDecodeError

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        with pytest.raises(InvalidResponseError, match="invalid JSON"):
            await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_openai_missing_choices_raises_invalid_response():
    client = _make_client()
    body = {"usage": {}}  # missing "choices"
    resp = _mock_response(200, body)

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        with pytest.raises(InvalidResponseError):
            await client.generate_response([{"role": "user", "content": "hi"}])
