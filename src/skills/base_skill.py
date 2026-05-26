import json
from abc import ABC, abstractmethod
from pathlib import Path

from src.skills.models import SkillContext, SkillResult

# Load all skill prompt content once at module import time.
# Same pattern used by base_agent.py for skills.json.
_PROMPTS_PATH = Path(__file__).resolve().parents[2] / "config" / "skills_prompts.json"


def _load_prompts() -> dict:
    try:
        return json.loads(_PROMPTS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_SKILL_PROMPTS: dict = _load_prompts()


class BaseSkill(ABC):
    name: str = ""
    description: str = ""

    def _get_config(self) -> dict:
        """Return this skill's section from config/skills_prompts.json.

        Keyed by ``self.name`` (e.g. "evidence", "socratic").
        Returns an empty dict if the skill has no config entry, so callers
        can safely use ``.get(key, default)`` without extra guards.
        """
        return _SKILL_PROMPTS.get(self.name, {})

    @abstractmethod
    def score(self, context: SkillContext) -> float:
        """Return a relevance score 0.0–1.0. 0.0 means do not run this skill."""

    def can_handle(self, context: SkillContext) -> bool:
        """Backward-compatible gate. True iff score() > 0.0."""
        return self.score(context) > 0.0

    @abstractmethod
    def run(self, context: SkillContext) -> SkillResult:
        """Execute the skill and return a SkillResult.

        Skills return structured context/text — they do NOT call LLMs directly.
        """
