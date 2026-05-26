import pytest

from src.sdk.zai_client import ZaiClient


@pytest.mark.asyncio
async def test_zai_client_generate_response(monkeypatch):
    calls = {}

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "zai response"}}]}

        def raise_for_status(self):
            pass

    async def mock_post(self, url, headers=None, json=None):
        calls.update({"url": url, "headers": headers, "json": json})
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    result = await client.generate_response([{"role": "user", "content": "Hi"}])

    assert result == "zai response"
    assert calls["url"] == "https://api.z.ai/api/paas/v4/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer key"
    assert calls["json"]["model"] == "glm-4-flash"


@pytest.mark.asyncio
async def test_zai_timeout_raises_provider_timeout(monkeypatch):
    import httpx

    from src.sdk.exceptions import ProviderTimeoutError

    async def mock_post(self, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    with pytest.raises(ProviderTimeoutError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_zai_rate_limit_raises(monkeypatch):
    from src.sdk.exceptions import RateLimitError

    class MockResponse:
        status_code = 429
        is_success = False
        text = "rate limited"
        def json(self): return {}

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    with pytest.raises(RateLimitError):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_zai_json_decode_error_raises(monkeypatch):
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
    client = ZaiClient("glm-4-flash", "key")
    with pytest.raises(InvalidResponseError, match="invalid JSON"):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_zai_empty_content_raises(monkeypatch):
    from src.sdk.exceptions import InvalidResponseError

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""
        def json(self):
            return {"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]}

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    with pytest.raises(InvalidResponseError, match="empty content"):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_zai_empty_content_with_finish_reason_length_raises(monkeypatch):
    """finish_reason='length' with truly empty content must still raise, not silently pass."""
    from src.sdk.exceptions import InvalidResponseError

    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            # Simulates GLM returning finish_reason='length' but zero content bytes —
            # the model consumed the entire budget on the prompt, leaving nothing for output.
            return {
                "choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                "usage": {"prompt_tokens": 512, "completion_tokens": 0, "total_tokens": 512},
            }

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    with pytest.raises(InvalidResponseError, match="empty content"):
        await client.generate_response([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_zai_partial_content_with_finish_reason_length_returned(monkeypatch):
    """finish_reason='length' with non-empty content is returned as-is (not raised)."""
    class MockResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "AI is beneficial"}, "finish_reason": "length"}
                ],
                "usage": {"prompt_tokens": 480, "completion_tokens": 32, "total_tokens": 512},
            }

    async def mock_post(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    client = ZaiClient("glm-4-flash", "key")
    result = await client.generate_response([{"role": "user", "content": "hi"}])
    assert result == "AI is beneficial"
