from src.shared.config import ConfigManager


def test_config_load():
    config = ConfigManager()
    assert config.total_rounds == 10
    assert config.openai_model == "gpt-4"
    assert config.max_rounds == 10
    assert config.default_topic == "Is AI a threat?"
    assert "openrouter" in config.available_providers
    assert config.provider_labels["openrouter"] == "OpenRouter"
    assert config.server_max_concurrent_debates == 3

def test_config_get_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini_key")
    monkeypatch.setenv("GROQ_API_KEY", "groq_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unused_key")
    config = ConfigManager()
    assert config.get_api_key("openai") == "test_key"
    assert config.get_api_key("gemini") == "gemini_key"
    assert config.get_api_key("groq") == "groq_key"
    assert config.get_api_key("openrouter") == "openrouter_key"
    assert config.get_api_key("anthropic") == ""


def test_config_get_model():
    config = ConfigManager()
    assert config.get_model("gemini") == "gemini-2.5-flash"
    assert config.get_model("groq") == "llama-3.1-8b-instant"


def test_env_example_matches_supported_providers():
    env_template = ConfigManager().config_path.parents[1] / ".env.example"
    content = env_template.read_text(encoding="utf-8")

    for key in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "ZAI_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        assert f"{key}=" in content
    assert "ANTHROPIC_API_KEY" not in content
