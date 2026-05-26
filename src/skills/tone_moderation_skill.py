from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_INSTRUCTION = "Be direct and assertive. Avoid aggressive language. No personal attacks."


class ToneModerationSkill(BaseSkill):
    name = "tone_moderation"
    description = "Ensures assertive but respectful tone"

    def can_handle(self, context: SkillContext) -> bool:
        return True

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        content = cfg.get("instruction", _DEFAULT_INSTRUCTION)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="always applicable",
            content=content,
        )
