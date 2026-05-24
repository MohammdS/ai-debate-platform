from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class EvidenceSkill(BaseSkill):
    name = "evidence"
    description = "Suggests evidence-based framing for the argument"

    def can_handle(self, context: SkillContext) -> bool:
        return context.skill_type == "evidence_based"

    def run(self, context: SkillContext) -> SkillResult:
        topic_hint = f" about '{context.topic}'" if context.topic else ""
        content = (
            f"Support your argument{topic_hint} with concrete facts, data, or "
            "widely recognised evidence. Cite the source or institution behind "
            "each claim. Avoid invented statistics."
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type is evidence_based",
            content=content,
        )
