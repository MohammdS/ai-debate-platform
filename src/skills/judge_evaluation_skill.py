"""JudgeEvaluationSkill — structures judge scoring criteria.

Key changes vs. prior version:
  • Penalises named sources that appear invented or lack verifiable attribution.
  • Penalises factual claims that contradict widely accepted facts.
  • Named sources without author/year/institution context score ZERO for evidence.
  • All penalty amounts are configurable in config/skills_prompts.json.
"""
from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_TRIGGER = "judge"
_DEFAULT_CRITERIA = ["Logic", "Evidence Quality", "Rebuttal Quality", "Relevance", "Clarity"]
_DEFAULT_BONUS = 5
_DEFAULT_PENALTY = 3
_DEFAULT_NAMED_SRC_PENALTY = 5
_DEFAULT_TIEBREAK = "Rebuttal Quality"


class JudgeEvaluationSkill(BaseSkill):
    name = "judge_evaluation"
    description = "Structures judge evaluation; penalises invented or unsupported named sources"

    def can_handle(self, context: SkillContext) -> bool:
        cfg = self._get_config()
        return context.skill_type == cfg.get("skill_type_trigger", _DEFAULT_TRIGGER)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        criteria = cfg.get("criteria", _DEFAULT_CRITERIA)
        bonus = cfg.get("citation_bonus", _DEFAULT_BONUS)
        penalty = cfg.get("uncited_penalty", _DEFAULT_PENALTY)
        named_src_penalty = cfg.get("named_source_penalty", _DEFAULT_NAMED_SRC_PENALTY)
        tiebreak = cfg.get("tiebreak_criterion", _DEFAULT_TIEBREAK)

        content = (
            f"Evaluate: {', '.join(criteria)}.\n"
            f"EVIDENCE SCORING:\n"
            f"  +{bonus} pts — each well-cited, verifiable factual claim.\n"
            f"  -{penalty} pts — each uncited factual assertion (specific stats, dates, or studies).\n"
            f"  -{named_src_penalty} pts — each named source ('According to X...') that:\n"
            "      (a) appears invented or cannot be confirmed from general knowledge,\n"
            "      (b) lacks attribution (author / year / institution), or\n"
            "      (c) contradicts a widely accepted fact.\n"
            "Named sources without proper attribution score ZERO for evidence "
            "and incur the full named-source penalty.\n"
            "You MUST declare exactly one winner. A tie is never acceptable.\n"
            f"If scores are equal, break on {tiebreak}."
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type matches trigger",
            content=content,
        )
