import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sdk.exceptions import InvalidResponseError, ProviderHTTPError, RateLimitError
from src.sdk.openrouter_client import OpenRouterClient


def _client() -> OpenRouterClient:
    return OpenRouterClient("openai/gpt-oss-120b:free", "test-key")


def _response(status: int, body: dict | str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.is_success = 200 <= status < 300
    if isinstance(body, dict):
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        resp.text = body
    return resp


@pytest.mark.asyncio
async def test_openrouter_success_posts_model_and_returns_content():
    body = {
        "choices": [{"message": {"content": "There are three r's."}}],
        "usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10},
    }
    resp = _response(200, body)
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)) as post:
        result = await _client().generate_response([{"role": "user", "content": "hi"}])
    assert result == "There are three r's."
    assert post.call_args.kwargs["json"]["model"] == "openai/gpt-oss-120b:free"
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_openrouter_stores_usage():
    resp = _response(200, {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    })
    client = _client()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
        await client.generate_response([{"role": "user", "content": "hi"}])
    assert client.last_usage["total_tokens"] == 3


@pytest.mark.asyncio
async def test_openrouter_rate_limit_and_http_errors():
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_response(429, "slow down"))), pytest.raises(RateLimitError):
        await _client().generate_response([{"role": "user", "content": "hi"}])
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_response(500, "server"))), pytest.raises(ProviderHTTPError):
        await _client().generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_openrouter_invalid_json_raises():
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_response(200, "<html>"))), pytest.raises(InvalidResponseError):
        await _client().generate_response([{"role": "user", "content": "hi"}])
