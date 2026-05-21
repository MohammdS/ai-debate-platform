
import httpx

from src.sdk.base_client import BaseAIClient


class OpenAIClient(BaseAIClient):
    """Client for interacting with OpenAI API."""

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Sends a chat completion request to OpenAI."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
