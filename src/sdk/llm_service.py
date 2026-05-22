import json
from pathlib import Path

from src.sdk.base_client import BaseAIClient
from src.sdk.factory import AIClientFactory
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper

_MODELS_PATH = Path(__file__).resolve().parents[2] / "config" / "models.json"


class LLMService:
    """
    Role-based LLM provider router.

    Reads config/models.json to determine which provider and model to use
    for each agent role (debater_a, debater_b, judge). Falls back to
    "default" if a role is not explicitly configured.

    Usage:
        service = LLMService()
        client    = service.get_client("judge")       # GeminiClient
        gatekeeper = service.get_gatekeeper("judge")  # per-provider limits
    """

    def __init__(self, config_path: Path = _MODELS_PATH,
                 override_provider: str | None = None):
        self._config = self._load(config_path)
        self._cfg_manager = ConfigManager()
        self._override = override_provider
        self._debate_cfg = self._cfg_manager.config_data.get("debate", {})

    @staticmethod
    def _load(path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {"default": {"provider": "mock", "model": "mock-model"}}

    def _role_config(self, role: str) -> dict:
        return self._config.get(role) or self._config.get("default", {})

    def provider_for(self, role: str) -> str:
        if self._override:
            return self._override
        return self._role_config(role).get("provider", "mock")

    def model_for(self, role: str) -> str:
        if self._override:
            return self._cfg_manager.get_model(self._override)
        return self._role_config(role).get("model", "mock-model")

    def _gen_params(self, role: str) -> tuple[int, float]:
        """Return (max_tokens, temperature) for the given role."""
        temperature = float(self._debate_cfg.get("temperature", 0.7))
        if role == "judge":
            max_tokens = int(self._debate_cfg.get("judge_max_tokens", 250))
        else:
            max_tokens = int(self._debate_cfg.get("debater_max_tokens", 180))
        return max_tokens, temperature

    def get_client(self, role: str) -> BaseAIClient:
        """Return an AI client configured for the given agent role."""
        provider = self.provider_for(role)
        model    = self.model_for(role)
        api_key  = self._cfg_manager.get_api_key(provider)
        max_tokens, temperature = self._gen_params(role)
        return AIClientFactory.create_client(provider, model, api_key,
                                             max_tokens=max_tokens,
                                             temperature=temperature)

    def get_gatekeeper(self, role: str) -> ApiGatekeeper:
        """Return a gatekeeper with rate limits for the role's provider."""
        return ApiGatekeeper(provider=self.provider_for(role))
