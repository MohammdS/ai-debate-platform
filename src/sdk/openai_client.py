import json

import httpx

from src.sdk.base_client import BaseAIClient
from src.sdk.exceptions import (
    InvalidResponseError,
    ProviderHTTPError,
    ProviderTimeoutError,
    RateLimitError,
)


class OpenAIClient(BaseAIClient):
    """Client for interacting with OpenAI API."""

    _BASE_URL = "https://api.openai.com/v1/chat/completions"

    async def generate_response(self, messages: list[dict]) -> str:
        """Sends a chat completion request to OpenAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(self._BASE_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("OpenAI request timed out") from exc

        if response.status_code == 429:
            raise RateLimitError(f"OpenAI rate limit exceeded: {response.text[:200]}")
        if not response.is_success:
            raise ProviderHTTPError(response.status_code, response.text)

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise InvalidResponseError(f"OpenAI returned invalid JSON: {response.text[:200]}") from exc
        self._store_usage(data)
        return self._validate_response_shape(data, ["choices", 0, "message", "content"])
