import asyncio
import time

import httpx
import jwt

from src.sdk.base_client import BaseAIClient


class ZhipuClient(BaseAIClient):
    """Client for Zhipu AI's OpenAI-compatible chat completions API."""

    _BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    # Lazy semaphore — created inside the running event loop to avoid loop-binding issues
    _semaphore: asyncio.Semaphore | None = None

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        loop = asyncio.get_event_loop()
        if cls._semaphore is None or cls._semaphore._loop is not loop:  # type: ignore[attr-defined]
            cls._semaphore = asyncio.Semaphore(1)
        return cls._semaphore

    def _generate_token(self) -> str:
        # Zhipu keys are "<id>.<secret>" — must be signed as JWT, not passed raw
        api_id, api_secret = self.api_key.split(".", 1)
        now = int(time.time() * 1000)
        payload = {"api_key": api_id, "exp": now + 60_000, "timestamp": now}
        return jwt.encode(payload, api_secret, algorithm="HS256", headers={"alg": "HS256", "sign_type": "SIGN"})

    def _normalize_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        # glm-4.7-flash does not support role=system; prepend it to the first user message
        if messages and messages[0]["role"] == "system":
            system_content = messages[0]["content"]
            rest = messages[1:]
            if rest and rest[0]["role"] == "user":
                rest[0] = {"role": "user", "content": f"{system_content}\n\n{rest[0]['content']}"}
            else:
                rest = [{"role": "user", "content": system_content}] + rest
            return rest
        return messages

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Sends a chat completion request to Zhipu AI."""
        headers = {
            "Authorization": f"Bearer {self._generate_token()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": self._normalize_messages(messages),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        async with self._get_semaphore():
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self._BASE_URL, headers=headers, json=payload)
            await asyncio.sleep(1.0)  # brief gap between releases to avoid burst 429s
            if not response.is_success:
                raise httpx.HTTPStatusError(
                    f"{response.status_code} — body: {response.text[:500]}",
                    request=response.request,
                    response=response,
                )
            data = response.json()
            return data["choices"][0]["message"]["content"]
