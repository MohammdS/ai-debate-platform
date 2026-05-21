from abc import ABC, abstractmethod


class BaseAIClient(ABC):
    """Abstract base class for all AI provider clients."""

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    async def generate_response(self, messages: list[dict[str, str]]) -> str:
        """Generates a response from the AI model."""
        pass
