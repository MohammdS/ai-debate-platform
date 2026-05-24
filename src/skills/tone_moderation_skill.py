from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class ToneModerationSkill(BaseSkill):
    name = "tone_moderation"
    description = "Ensures assertive but respectful tone"

    def can_handle(self, context: SkillContext) -> bool:
        return True

    def run(self, context: SkillContext) -> SkillResult:
        content = "Be direct and assertive. Avoid aggressive language. No personal attacks."
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="always applicable",
            content=content,
        )
