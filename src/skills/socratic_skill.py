from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class SocraticSkill(BaseSkill):
    name = "socratic"
    description = "Generates Socratic questioning approach targeting opponent's specific claim"

    def can_handle(self, context: SkillContext) -> bool:
        return context.skill_type == "socratic"

    def run(self, context: SkillContext) -> SkillResult:
        target = (
            f" their claim: '{context.opponent_last_message[:80].strip()}'"
            if context.opponent_last_message else ""
        )
        content = (
            f"Challenge opponent's assumptions{target} with probing questions. "
            "Use 'What evidence supports...?', 'How do you explain...?', "
            "'What are the consequences if you are wrong?'"
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type is socratic",
            content=content,
        )
