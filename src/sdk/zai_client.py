import asyncio
import json
import logging

import httpx

from src.sdk.base_client import BaseAIClient
from src.sdk.exceptions import (
    InvalidResponseError,
    ProviderHTTPError,
    ProviderTimeoutError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class ZaiClient(BaseAIClient):
    """Client for z.ai's OpenAI-compatible chat completions API."""

    _BASE_URL = "https://api.z.ai/api/paas/v4/chat/completions"
    _semaphore: asyncio.Semaphore | None = None
    _semaphore_loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        if cls._semaphore is None or cls._semaphore_loop is not loop:
            cls._semaphore = asyncio.Semaphore(1)
            cls._semaphore_loop = loop
        return cls._semaphore

    async def generate_response(self, messages: list[dict]) -> str:
        """Sends a chat completion request to z.ai."""
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
            async with self._get_semaphore(), httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(self._BASE_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("z.ai request timed out") from exc

        if response.status_code == 429:
            raise RateLimitError(f"z.ai rate limit exceeded: {response.text[:200]}")
        if not response.is_success:
            raise ProviderHTTPError(response.status_code, response.text)

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise InvalidResponseError(f"z.ai returned invalid JSON: {response.text[:200]}") from exc
        self._store_usage(data)
        content = self._validate_response_shape(data, ["choices", 0, "message", "content"])
        finish_reason = data["choices"][0].get("finish_reason", "unknown")
        if not content.strip():
            raise InvalidResponseError(
                f"z.ai returned empty content (finish_reason={finish_reason!r})"
            )
        if finish_reason == "length":
            # Model hit max_tokens mid-generation — content is non-empty but truncated.
            # Return what we have; enforce_word_limit() in the caller will tidy it up.
            logger.warning(
                "z.ai response truncated by max_tokens (%d chars returned); "
                "consider raising debater_max_tokens in setup.json",
                len(content),
            )
        logger.debug("z.ai response received (%d chars, finish_reason=%r)", len(content), finish_reason)
        return content
