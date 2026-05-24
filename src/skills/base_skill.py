from abc import ABC, abstractmethod

from src.skills.models import SkillContext, SkillResult


class BaseSkill(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def can_handle(self, context: SkillContext) -> bool:
        """Return True if this skill applies to the given context."""

    @abstractmethod
    def run(self, context: SkillContext) -> SkillResult:
        """Execute the skill and return a SkillResult.

        Skills return structured context/text — they do NOT call LLMs directly.
        """
