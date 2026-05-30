import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Fallback labels keep tests and mock demos readable if setup.json is absent.
DEFAULT_PROVIDER_LABELS = {
    "groq": "Groq",
    "gemini": "Gemini",
    "openai": "OpenAI",
    "zai": "Z.ai",
    "openrouter": "OpenRouter",
    "mock": "Mock",
}


class ConfigManager:
    def __init__(self, config_path: str | None = None):
        config_path = config_path or str(Path(__file__).resolve().parents[2] / "config" / "setup.json")
        load_dotenv()
        self.config_path = Path(config_path)
        self.config_data = self._load_json_config()

    def _load_json_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def get_api_key(self, provider: str) -> str:
        key_map = {
            "openai":    "OPENAI_API_KEY",
            "gemini":    "GEMINI_API_KEY",
            "groq":      "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "zai":       "ZAI_API_KEY",
        }
        return os.getenv(key_map.get(provider.lower(), ""), "")

    def get_model(self, provider: str, default: str = "mock-model") -> str:
        return self.get_value("api", f"{provider.lower()}_model", default)

    def get_value(self, category: str, key: str, default=None):
        return self.config_data.get(category, {}).get(key, default)

    @property
    def openai_model(self) -> str:
        return self.get_value("api", "openai_model", "gpt-4")

    @property
    def total_rounds(self) -> int:
        return self.get_value("debate", "total_rounds", 20)

    @property
    def min_rounds(self) -> int:
        return int(self.get_value("debate", "min_rounds", 1))

    @property
    def max_rounds(self) -> int:
        return int(self.get_value("debate", "max_rounds", self.total_rounds))

    @property
    def http_timeout(self) -> float:
        return float(self.get_value("api", "http_timeout_seconds", 60.0))

    @property
    def stream_event_timeout(self) -> float:
        return float(self.get_value("api", "stream_event_timeout_seconds", 120.0))

    @property
    def default_provider_a(self) -> str:
        return self.get_value("defaults", "provider_a", self.available_providers[0])

    @property
    def default_provider_b(self) -> str:
        fallback = self.available_providers[1] if len(self.available_providers) > 1 else self.default_provider_a
        return self.get_value("defaults", "provider_b", fallback)

    @property
    def default_judge_provider(self) -> str:
        return self.get_value("defaults", "judge_provider", self.default_provider_b)

    @property
    def default_topic(self) -> str:
        return self.get_value("defaults", "topic", "")

    @property
    def default_stance_a(self) -> str:
        return self.get_value("defaults", "stance_a", "")

    @property
    def default_stance_b(self) -> str:
        return self.get_value("defaults", "stance_b", "")

    @property
    def menu_stance_a(self) -> str:
        return self.get_value("defaults", "menu_stance_a", self.default_stance_a)

    @property
    def menu_stance_b(self) -> str:
        return self.get_value("defaults", "menu_stance_b", self.default_stance_b)

    @property
    def available_providers(self) -> list[str]:
        providers = self.get_value("providers", "available")
        return providers or list(DEFAULT_PROVIDER_LABELS)

    @property
    def provider_labels(self) -> dict[str, str]:
        labels = self.get_value("providers", "labels", {}) or {}
        return {**DEFAULT_PROVIDER_LABELS, **labels}

    @property
    def server_host(self) -> str:
        return self.get_value("server", "host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return int(self.get_value("server", "port", 8000))

    @property
    def server_max_concurrent_debates(self) -> int:
        return int(self.get_value("server", "max_concurrent_debates", 3))

    @property
    def watchdog_timeout(self) -> float:
        return float(self.get_value("watchdog", "timeout_seconds", 600.0))

    @property
    def watchdog_max_failures(self) -> int:
        return int(self.get_value("watchdog", "max_failures", 3))

    @property
    def watchdog_poll_interval(self) -> float:
        return float(self.get_value("watchdog", "poll_interval_seconds", 5.0))

    @property
    def skill_type_a(self) -> str:
        return self.get_value("skills", "debater_a_skill", "evidence_based")

    @property
    def skill_type_b(self) -> str:
        return self.get_value("skills", "debater_b_skill", "socratic")
