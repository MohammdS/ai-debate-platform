from src.shared.config import ConfigManager


def test_config_load():
    config = ConfigManager()
    assert config.total_rounds == 10
    assert config.openai_model == "gpt-4"

def test_config_get_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini_key")
    monkeypatch.setenv("GROQ_API_KEY", "groq_key")
    config = ConfigManager()
    assert config.get_api_key("openai") == "test_key"
    assert config.get_api_key("gemini") == "gemini_key"
    assert config.get_api_key("groq") == "groq_key"


def test_config_get_model():
    config = ConfigManager()
    assert config.get_model("gemini") == "gemini-2.5-flash"
    assert config.get_model("groq") == "llama-3.1-8b-instant"
