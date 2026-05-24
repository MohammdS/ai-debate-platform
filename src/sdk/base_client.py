from abc import ABC, abstractmethod

from src.sdk.exceptions import InvalidResponseError, MissingAPIKeyError


class BaseAIClient(ABC):
    """Abstract base class for all AI provider clients."""

    def __init__(self, model_name: str, api_key: str,
                 max_tokens: int = 180, temperature: float = 0.7):
        self.model_name  = model_name
        self.api_key     = api_key
        self.max_tokens  = max_tokens
        self.temperature = temperature
        self.last_usage: dict = {}   # populated after each successful call
        self._check_api_key()

    def _check_api_key(self) -> None:
        """Raise MissingAPIKeyError if api_key is absent or blank."""
        if not self.api_key:
            raise MissingAPIKeyError(
                f"{self.__class__.__name__} requires a non-empty api_key"
            )

    def _store_usage(self, data: dict) -> None:
        """Extract OpenAI-format usage block and store in last_usage."""
        usage = data.get("usage", {})
        self.last_usage = {
            "prompt_tokens":     int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens":      int(usage.get("total_tokens", 0)),
        }

    def _store_gemini_usage(self, data: dict) -> None:
        """Extract Gemini usageMetadata block and store in last_usage."""
        meta = data.get("usageMetadata", {})
        prompt     = int(meta.get("promptTokenCount", 0))
        completion = int(meta.get("candidatesTokenCount", 0))
        self.last_usage = {
            "prompt_tokens":     prompt,
            "completion_tokens": completion,
            "total_tokens":      prompt + completion,
        }

    def _validate_response_shape(self, data: dict, path: list) -> str:
        """Walk *path* through *data* and return the string leaf value."""
        node = data
        traversed: list = []
        for key in path:
            try:
                node = node[key]
            except (KeyError, IndexError, TypeError) as exc:
                raise InvalidResponseError(
                    f"Missing key/index {key!r} at path {traversed} in response"
                ) from exc
            traversed.append(key)
        if not isinstance(node, str):
            raise InvalidResponseError(
                f"Expected str at path {traversed}, got {type(node).__name__}"
            )
        return node

    @abstractmethod
    async def generate_response(self, messages: list[dict]) -> str:
        """Generate a response from the AI model."""
