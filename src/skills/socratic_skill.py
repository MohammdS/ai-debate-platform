from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class SocraticSkill(BaseSkill):
    name = "socratic"
    description = "Generates Socratic questioning approach"

    def can_handle(self, context: SkillContext) -> bool:
        return context.skill_type == "socratic"

    def run(self, context: SkillContext) -> SkillResult:
        content = (
            "Challenge opponent's assumptions with probing questions. "
            "Use 'What evidence supports...?', 'How do you explain...?'"
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type is socratic",
            content=content,
        )
