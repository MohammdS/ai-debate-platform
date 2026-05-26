import pytest

from src.sdk.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_gemini_client_generate_response(monkeypatch):
    calls = {}

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "gemini response"}]}}]}

        def raise_for_status(self):
            pass

    async def mock_post(self, url, json=None):
        calls.update({"url": url, "json": json})
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GeminiClient("gemini-2.5-flash", "key")
    messages = [{"role": "system", "content": "Rules"}, {"role": "user", "content": "Hi"}]
    result = await client.generate_response(messages)

    assert result == "gemini response"
    assert "gemini-2.5-flash:generateContent?key=key" in calls["url"]
    assert calls["json"]["systemInstruction"]["parts"][0]["text"] == "Rules"
    assert calls["json"]["contents"][0]["parts"][0]["text"] == "Hi"


@pytest.mark.asyncio
async def test_gemini_client_seeds_first_turn(monkeypatch):
    calls = {}

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "first turn"}]}}]}

        def raise_for_status(self):
            pass

    async def mock_post(self, url, json=None):
        calls.update({"json": json})
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GeminiClient("gemini-2.5-flash", "key")
    result = await client.generate_response([{"role": "system", "content": "Rules"}])

    assert result == "first turn"
    assert calls["json"]["contents"][0]["parts"][0]["text"] == "Begin the debate."


@pytest.mark.asyncio
async def test_gemini_timeout_raises_provider_timeout(monkeypatch):
    import httpx

    from src.sdk.exceptions import ProviderTimeoutError

    async def mock_post(self, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GeminiClient("gemini-2.5-flash", "key")
    with pytest.raises(ProviderTimeoutError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_gemini_rate_limit_raises(monkeypatch):
    from src.sdk.exceptions import RateLimitError

    class MockResponse:
        status_code = 429
        is_success = False
        text = "rate limited"
        def json(self): return {}

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = GeminiClient("gemini-2.5-flash", "key")
    with pytest.raises(RateLimitError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_gemini_json_decode_error_raises(monkeypatch):
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
    client = GeminiClient("gemini-2.5-flash", "key")
    with pytest.raises(InvalidResponseError, match="invalid JSON"):
        await client.generate_response([{"role": "user", "content": "hi"}])
