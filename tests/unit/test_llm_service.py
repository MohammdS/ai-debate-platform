import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.sdk.factory import AIClientFactory
from src.sdk.gemini_client import GeminiClient
from src.sdk.groq_client import GroqClient
from src.sdk.llm_service import LLMService
from src.sdk.mock_client import MockAIClient
from src.sdk.openai_client import OpenAIClient


def make_models_config(tmp_path: Path) -> Path:
    config = {
        "debater_a": {"provider": "groq",   "model": "llama-3.1-8b-instant"},
        "debater_b": {"provider": "groq",   "model": "llama-3.1-8b-instant"},
        "judge":     {"provider": "gemini", "model": "gemini-2.5-flash"},
        "default":   {"provider": "mock",   "model": "mock-model"},
    }
    p = tmp_path / "models.json"
    p.write_text(json.dumps(config))
    return p


# --- provider routing ---

def test_debater_routes_to_groq(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    assert service.provider_for("debater_a") == "groq"
    assert service.provider_for("debater_b") == "groq"


def test_judge_routes_to_gemini(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    assert service.provider_for("judge") == "gemini"


def test_unknown_role_falls_back_to_default(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    assert service.provider_for("unknown_role") == "mock"


def test_override_provider_takes_precedence(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path),
                         override_provider="mock")
    assert service.provider_for("judge") == "mock"
    assert service.provider_for("debater_a") == "mock"


# --- model routing ---

def test_model_for_judge(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    assert service.model_for("judge") == "gemini-2.5-flash"


def test_model_for_debater(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    assert service.model_for("debater_a") == "llama-3.1-8b-instant"


# --- client creation with mocked factory ---

def test_get_client_calls_factory_with_correct_provider(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    with patch("src.sdk.llm_service.AIClientFactory.create_client") as mock_factory:
        mock_factory.return_value = MagicMock()
        service.get_client("judge")
        provider, model, _ = mock_factory.call_args[0]
        assert provider == "gemini"
        assert model == "gemini-2.5-flash"


def test_get_client_debater_uses_groq(tmp_path):
    service = LLMService(config_path=make_models_config(tmp_path))
    with patch("src.sdk.llm_service.AIClientFactory.create_client") as mock_factory:
        mock_factory.return_value = MagicMock()
        service.get_client("debater_a")
        provider, model, _ = mock_factory.call_args[0]
        assert provider == "groq"


# --- gatekeeper creation ---

def test_get_gatekeeper_returns_gatekeeper_for_provider(tmp_path):
    from src.shared.gatekeeper import ApiGatekeeper
    service = LLMService(config_path=make_models_config(tmp_path))
    gk = service.get_gatekeeper("judge")
    assert isinstance(gk, ApiGatekeeper)


# --- missing config fallback ---

def test_missing_config_file_falls_back_to_mock(tmp_path):
    service = LLMService(config_path=tmp_path / "nonexistent.json")
    assert service.provider_for("judge") == "mock"


# --- role_overrides ---

def test_role_overrides_judge_to_groq(tmp_path):
    service = LLMService(
        config_path=make_models_config(tmp_path),
        role_overrides={"judge": "groq"},
    )
    assert service.provider_for("judge") == "groq"


# --- factory creates correct client types ---

def test_factory_creates_mock_client():
    client = AIClientFactory.create_client("mock", "mock-model", "any-key")
    assert isinstance(client, MockAIClient)


def test_factory_creates_groq_client():
    client = AIClientFactory.create_client("groq", "llama3", "real-key")
    assert isinstance(client, GroqClient)


def test_factory_creates_gemini_client():
    client = AIClientFactory.create_client("gemini", "gemini-pro", "real-key")
    assert isinstance(client, GeminiClient)


def test_factory_creates_openai_client():
    client = AIClientFactory.create_client("openai", "gpt-4", "real-key")
    assert isinstance(client, OpenAIClient)
