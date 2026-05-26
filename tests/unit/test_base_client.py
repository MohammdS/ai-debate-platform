import pytest

from src.sdk.base_client import BaseAIClient
from src.sdk.exceptions import InvalidResponseError, MissingAPIKeyError
from src.sdk.groq_client import GroqClient
from src.sdk.mock_client import MockAIClient

# --- MockAIClient ---

def test_mock_client_allows_empty_api_key():
    """MockAIClient overrides _check_api_key to be a no-op."""
    client = MockAIClient(model_name="mock", api_key="")
    assert client.api_key == ""


def test_mock_client_allows_none_api_key():
    client = MockAIClient(model_name="mock", api_key=None)
    assert client.api_key is None


# --- Real client: MissingAPIKeyError ---

def test_groq_client_raises_missing_api_key_on_empty_string():
    with pytest.raises(MissingAPIKeyError):
        GroqClient(model_name="llama3", api_key="")


def test_groq_client_raises_missing_api_key_on_none():
    with pytest.raises(MissingAPIKeyError):
        GroqClient(model_name="llama3", api_key=None)


def test_groq_client_succeeds_with_valid_key():
    client = GroqClient(model_name="llama3", api_key="sk-test-key")
    assert client.api_key == "sk-test-key"


# --- Minimal concrete subclass for _validate_response_shape ---

class _MinimalClient(BaseAIClient):
    def _check_api_key(self) -> None:
        pass  # skip for test isolation

    async def generate_response(self, messages):
        return ""


def test_validate_response_shape_happy_path():
    client = _MinimalClient("m", "k")
    data = {"choices": [{"message": {"content": "hello"}}]}
    result = client._validate_response_shape(data, ["choices", 0, "message", "content"])
    assert result == "hello"


def test_validate_response_shape_missing_key():
    client = _MinimalClient("m", "k")
    data = {"choices": [{"message": {}}]}
    with pytest.raises(InvalidResponseError, match="content"):
        client._validate_response_shape(data, ["choices", 0, "message", "content"])


def test_validate_response_shape_index_out_of_range():
    client = _MinimalClient("m", "k")
    data = {"choices": []}
    with pytest.raises(InvalidResponseError):
        client._validate_response_shape(data, ["choices", 0, "message"])


def test_validate_response_shape_wrong_type():
    client = _MinimalClient("m", "k")
    data = {"result": 42}
    with pytest.raises(InvalidResponseError, match="int"):
        client._validate_response_shape(data, ["result"])
