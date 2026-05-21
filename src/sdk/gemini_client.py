import httpx

from src.sdk.base_client import BaseAIClient


class GeminiClient(BaseAIClient):
    """Client for the Gemini Developer API."""

    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Sends a generateContent request to Gemini."""
        url = self._url()
        payload = {
            "systemInstruction": self._system_instruction(messages),
            "contents": self._contents(messages),
            "generationConfig": {"temperature": 0.7},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _url(self) -> str:
        model = self.model_name
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

    def _system_instruction(self, messages: list[dict[str, str]]) -> dict:
        text = "\n".join(m["content"] for m in messages if m["role"] == "system")
        return {"parts": [{"text": text}]}

    def _contents(self, messages: list[dict[str, str]]) -> list[dict]:
        contents = []
        for message in messages:
            if message["role"] == "system":
                continue
            role = "model" if message["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message["content"]}]})
        return contents
