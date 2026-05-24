from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult


class JudgeEvaluationSkill(BaseSkill):
    name = "judge_evaluation"
    description = "Structures judge's evaluation criteria and enforces no-tie rule"

    def can_handle(self, context: SkillContext) -> bool:
        return context.skill_type == "judge"

    def run(self, context: SkillContext) -> SkillResult:
        content = (
            "Evaluate: Logic, Evidence Quality, Rebuttal Quality, Relevance, Clarity.\n"
            "EVIDENCE SCORING: Award +5 bonus points for each well-cited factual claim "
            "(formatted as [source: filename]). Deduct -3 points for each uncited factual "
            "assertion that relies on specific statistics, dates, or studies.\n"
            "You MUST declare exactly one winner. A tie is never acceptable.\n"
            "If scores are equal, break on Rebuttal Quality."
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type is judge",
            content=content,
        )
