from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_TRIGGER = "evidence_based"
_DEFAULT_TEMPLATE = (
    "Support your argument{topic_hint} with concrete facts, data, or "
    "widely recognised evidence. Cite the source or institution behind "
    "each claim. Avoid invented statistics."
)


class EvidenceSkill(BaseSkill):
    name = "evidence"
    description = "Suggests evidence-based framing for the argument"

    def can_handle(self, context: SkillContext) -> bool:
        cfg = self._get_config()
        return context.skill_type == cfg.get("skill_type_trigger", _DEFAULT_TRIGGER)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        topic_hint = f" about '{context.topic}'" if context.topic else ""
        template = cfg.get("template", _DEFAULT_TEMPLATE)
        content = template.replace("{topic_hint}", topic_hint)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type matches trigger",
            content=content,
        )
