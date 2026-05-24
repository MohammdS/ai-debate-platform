from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class SummarizationSkill(BaseSkill):
    name = "summarization"
    description = "Summarizes the debate so far for context"

    def can_handle(self, context: SkillContext) -> bool:
        return len(context.transcript) >= 4

    def run(self, context: SkillContext) -> SkillResult:
        last_four = context.transcript[-4:]
        lines = []
        for entry in last_four:
            name = entry.get("name", entry.get("role", "Unknown"))
            text = entry.get("content", "")[:80]
            lines.append(f"{name}: {text}")
        summary = "Recent debate summary:\n" + "\n".join(lines)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="transcript has >= 4 entries",
            content=summary,
        )
