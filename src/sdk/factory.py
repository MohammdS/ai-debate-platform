from src.sdk.base_client import BaseAIClient
from src.sdk.mock_client import MockAIClient
from src.sdk.openai_client import OpenAIClient


class AIClientFactory:
    """Factory for creating AI provider clients."""

    @staticmethod
    def create_client(provider: str, model_name: str, api_key: str) -> BaseAIClient:
        """Instantiates the requested AI client."""
        provider = provider.lower()
        if provider == "openai":
            return OpenAIClient(model_name, api_key)
        if provider == "mock":
            return MockAIClient(model_name, api_key)
        raise ValueError(f"Unsupported provider: {provider}")
