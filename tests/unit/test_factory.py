import pytest

from src.sdk.factory import AIClientFactory
from src.sdk.gemini_client import GeminiClient
from src.sdk.groq_client import GroqClient
from src.sdk.mock_client import MockAIClient
from src.sdk.openai_client import OpenAIClient
from src.sdk.openrouter_client import OpenRouterClient


def test_factory_create_openai():
    client = AIClientFactory.create_client("openai", "model", "key")
    assert isinstance(client, OpenAIClient)


def test_factory_create_openrouter():
    client = AIClientFactory.create_client("openrouter", "model", "key")
    assert isinstance(client, OpenRouterClient)


def test_factory_create_mock():
    client = AIClientFactory.create_client("mock", "model", "key")
    assert isinstance(client, MockAIClient)


def test_factory_create_gemini():
    client = AIClientFactory.create_client("gemini", "model", "key")
    assert isinstance(client, GeminiClient)


def test_factory_create_groq():
    client = AIClientFactory.create_client("groq", "model", "key")
    assert isinstance(client, GroqClient)


def test_factory_invalid_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        AIClientFactory.create_client("invalid", "model", "key")
