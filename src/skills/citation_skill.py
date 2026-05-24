from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class CitationSkill(BaseSkill):
    name = "citation"
    description = "Reminds debater to cite sources or flag uncited claims"

    def can_handle(self, context: SkillContext) -> bool:
        return True

    def run(self, context: SkillContext) -> SkillResult:
        content = (
            "If citing facts, name the source. "
            "If opponent made uncited claims, challenge them."
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="always applicable",
            content=content,
        )
