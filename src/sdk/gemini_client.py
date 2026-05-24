import httpx

from src.sdk.base_client import BaseAIClient
from src.sdk.exceptions import ProviderHTTPError, ProviderTimeoutError, RateLimitError


class GeminiClient(BaseAIClient):
    """Client for the Gemini Developer API."""

    async def generate_response(self, messages: list[dict]) -> str:
        """Sends a generateContent request to Gemini."""
        url = self._url()
        payload = {
            "systemInstruction": self._system_instruction(messages),
            "contents": self._contents(messages),
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Gemini request timed out") from exc

        if response.status_code == 429:
            raise RateLimitError(f"Gemini rate limit exceeded: {response.text[:200]}")
        if not response.is_success:
            raise ProviderHTTPError(response.status_code, response.text)

        data = response.json()
        self._store_gemini_usage(data)
        return self._validate_response_shape(
            data, ["candidates", 0, "content", "parts", 0, "text"]
        )

    def _url(self) -> str:
        model = self.model_name
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )

    def _system_instruction(self, messages: list[dict]) -> dict:
        text = "\n".join(m["content"] for m in messages if m["role"] == "system")
        return {"parts": [{"text": text}]}

    def _contents(self, messages: list[dict]) -> list[dict]:
        contents = []
        for message in messages:
            if message["role"] == "system":
                continue
            role = "model" if message["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message["content"]}]})
        return contents or [{"role": "user", "parts": [{"text": "Begin the debate."}]}]
