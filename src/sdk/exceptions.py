"""Custom exceptions for the AI SDK layer."""


class AIClientError(Exception):
    """Base exception for all AI client errors."""


class MissingAPIKeyError(AIClientError):
    """Raised when an API key is missing or empty."""


class ProviderHTTPError(AIClientError):
    """Raised on non-2xx HTTP responses from a provider."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body[:200]}")


class ProviderTimeoutError(AIClientError):
    """Raised when a provider request times out."""


class RateLimitError(AIClientError):
    """Raised when a provider returns HTTP 429 Too Many Requests."""


class InvalidResponseError(AIClientError):
    """Raised when a provider response has an unexpected shape."""
