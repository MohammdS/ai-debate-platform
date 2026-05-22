import asyncio
import logging

import httpx

from src.sdk.base_client import BaseAIClient

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

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
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

        async with self._get_semaphore():
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self._BASE_URL, headers=headers, json=payload)

        if not response.is_success:
            raise httpx.HTTPStatusError(
                f"{response.status_code} — body: {response.text[:500]}",
                request=response.request,
                response=response,
            )
        data = response.json()
        content = data["choices"][0]["message"].get("content") or ""
        if not content.strip():
            finish_reason = data["choices"][0].get("finish_reason", "unknown")
            raise ValueError(
                f"z.ai returned empty content (finish_reason={finish_reason!r}). "
                f"Full choice: {data['choices'][0]}"
            )
        logger.debug("z.ai response received (%d chars)", len(content))
        return content
