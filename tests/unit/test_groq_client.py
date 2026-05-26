import pytest

from src.sdk.groq_client import GroqClient


@pytest.mark.asyncio
async def test_groq_client_generate_response(monkeypatch):
    calls = {}

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "groq response"}}]}

        def raise_for_status(self):
            pass

    async def mock_post(self, url, headers=None, json=None):
        calls.update({"url": url, "headers": headers, "json": json})
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GroqClient("llama-3.1-8b-instant", "key")
    result = await client.generate_response([{"role": "user", "content": "Hi"}])

    assert result == "groq response"
    assert calls["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer key"
    assert calls["json"]["model"] == "llama-3.1-8b-instant"


@pytest.mark.asyncio
async def test_groq_timeout_raises_provider_timeout(monkeypatch):
    import httpx

    from src.sdk.exceptions import ProviderTimeoutError

    async def mock_post(self, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GroqClient("llama-3.1-8b-instant", "key")
    with pytest.raises(ProviderTimeoutError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_groq_rate_limit_raises(monkeypatch):
    from src.sdk.exceptions import RateLimitError

    class MockResponse:
        status_code = 429
        is_success = False
        text = "rate limited"
        def json(self): return {}

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GroqClient("llama-3.1-8b-instant", "key")
    with pytest.raises(RateLimitError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_groq_json_decode_error_raises(monkeypatch):
    import json

    from src.sdk.exceptions import InvalidResponseError

    class MockResponse:
        status_code = 200
        is_success = True
        text = "<html>bad</html>"
        def json(self): raise json.JSONDecodeError("bad", "", 0)

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GroqClient("llama-3.1-8b-instant", "key")
    with pytest.raises(InvalidResponseError, match="invalid JSON"):
        await client.generate_response([{"role": "user", "content": "hi"}])
