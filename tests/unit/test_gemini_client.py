import pytest

from src.sdk.gemini_client import GeminiClient


@pytest.mark.asyncio
async def test_gemini_client_generate_response(monkeypatch):
    calls = {}

    class MockResponse:
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
