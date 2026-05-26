import json
import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigManager:
    """Manages application configuration from JSON and environment variables."""

    def __init__(self, config_path: str | None = None):
        config_path = config_path or str(Path(__file__).resolve().parents[2] / "config" / "setup.json")
        load_dotenv()
        self.config_path = Path(config_path)
        self.config_data = self._load_json_config()

    def _load_json_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return json.load(f)

    def get_api_key(self, provider: str) -> str:
        """Retrieves API key for a given provider from environment variables."""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "zai": "ZAI_API_KEY",

        }
        return os.getenv(key_map.get(provider.lower(), ""), "")

    def get_model(self, provider: str, default: str = "mock-model") -> str:
        """Retrieves the configured model for a provider."""
        return self.get_value("api", f"{provider.lower()}_model", default)

    def get_value(self, category: str, key: str, default=None):
        """Retrieves a value from the JSON config."""
        return self.config_data.get(category, {}).get(key, default)

    @property
    def openai_model(self) -> str:
        return self.get_value("api", "openai_model", "gpt-4")

    @property
    def total_rounds(self) -> int:
        return self.get_value("debate", "total_rounds", 20)
