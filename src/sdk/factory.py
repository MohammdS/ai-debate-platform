from src.sdk.base_client import BaseAIClient
from src.sdk.gemini_client import GeminiClient
from src.sdk.groq_client import GroqClient
from src.sdk.mock_client import MockAIClient
from src.sdk.openai_client import OpenAIClient
from src.sdk.zhipu_client import ZhipuClient


class AIClientFactory:
    """Factory for creating AI provider clients."""

    @staticmethod
    def create_client(
        provider: str,
        model_name: str,
        api_key: str,
        max_tokens: int = 180,
        temperature: float = 0.7,
    ) -> BaseAIClient:
        """Instantiates the requested AI client."""
        provider = provider.lower()
        kwargs = {"max_tokens": max_tokens, "temperature": temperature}
        if provider == "openai":
            return OpenAIClient(model_name, api_key, **kwargs)
        if provider == "gemini":
            return GeminiClient(model_name, api_key, **kwargs)
        if provider == "groq":
            return GroqClient(model_name, api_key, **kwargs)
        if provider == "mock":
            return MockAIClient(model_name, api_key, **kwargs)
        if provider == "zhipu":
            return ZhipuClient(model_name, api_key, **kwargs)
        raise ValueError(f"Unsupported provider: {provider}")
