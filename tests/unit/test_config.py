from src.shared.config import ConfigManager


def test_config_load():
    config = ConfigManager()
    assert config.total_rounds == 20
    assert config.openai_model == "gpt-4"

def test_config_get_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    config = ConfigManager()
    assert config.get_api_key("openai") == "test_key"
