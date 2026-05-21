import pytest

from src.sdk.factory import AIClientFactory
from src.sdk.mock_client import MockAIClient
from src.sdk.openai_client import OpenAIClient


def test_factory_create_openai():
    client = AIClientFactory.create_client("openai", "model", "key")
    assert isinstance(client, OpenAIClient)

def test_factory_create_mock():
    client = AIClientFactory.create_client("mock", "model", "key")
    assert isinstance(client, MockAIClient)

def test_factory_invalid_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        AIClientFactory.create_client("invalid", "model", "key")
