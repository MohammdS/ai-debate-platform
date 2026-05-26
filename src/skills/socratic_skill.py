from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_TRIGGER = "socratic"
_DEFAULT_INTRO = "Challenge opponent's assumptions{target} with probing questions."
_DEFAULT_QUESTIONS = [
    "What evidence supports...?",
    "How do you explain...?",
    "What are the consequences if you are wrong?",
]


class SocraticSkill(BaseSkill):
    name = "socratic"
    description = "Generates Socratic questioning approach targeting opponent's specific claim"

    def can_handle(self, context: SkillContext) -> bool:
        cfg = self._get_config()
        return context.skill_type == cfg.get("skill_type_trigger", _DEFAULT_TRIGGER)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        target = (
            f" their claim: '{context.opponent_last_message[:80].strip()}'"
            if context.opponent_last_message else ""
        )
        intro = cfg.get("intro", _DEFAULT_INTRO).replace("{target}", target)
        questions = cfg.get("question_templates", _DEFAULT_QUESTIONS)
        content = intro + " Use " + ", ".join(f"'{q}'" for q in questions)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type matches trigger",
            content=content,
        )
