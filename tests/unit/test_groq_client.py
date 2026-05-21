import pytest

from src.sdk.groq_client import GroqClient


@pytest.mark.asyncio
async def test_groq_client_generate_response(monkeypatch):
    calls = {}

    class MockResponse:
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
