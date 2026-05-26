"""RebuttalSkill — targets the opponent's most specific/vulnerable claim.

Priority for "strongest" claim:
  1. Sentence containing a number, %, year, or named entity — most falsifiable.
  2. Longest sentence — most specific claim.
  3. Full message truncated to _FALLBACK_CHARS.

Template configurable in config/skills_prompts.json under "rebuttal".
"""
from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_SENTENCE_SPLIT = re.compile(r"[.!?]+")
_DATA_SIGNAL = re.compile(
    r"\d+(?:\.\d+)?(?:\s*%|\s*(?:billion|million|trillion|percent))|"
    r"\b(?:study|research|report|according to|data shows?|found that)\b",
    re.I,
)
_FALLBACK_CHARS = 120


def _pick_target(message: str) -> str:
    """Return the most attackable sentence from the opponent's message."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(message) if len(s.strip()) > 15]
    if not sentences:
        return message[:_FALLBACK_CHARS]

    # Prefer a sentence that contains a data/stat signal — easiest to challenge
    data_sentences = [s for s in sentences if _DATA_SIGNAL.search(s)]
    pool = data_sentences if data_sentences else sentences
    return max(pool, key=len)[:_FALLBACK_CHARS]


_DEFAULT_ATTACK_TEMPLATE = (
    'Directly refute this claim: "{strongest_claim}". '
    "Show why it is wrong, overstated, or unsupported. "
    "Then introduce ONE new argument angle not yet raised in this debate."
)


class RebuttalSkill(BaseSkill):
    name = "rebuttal"
    description = "Targets the opponent's most specific/data-driven claim and demands a new point"

    def can_handle(self, context: SkillContext) -> bool:
        return context.round_num > 1 and bool(context.opponent_last_message)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        template = cfg.get("attack_template", _DEFAULT_ATTACK_TEMPLATE)
        target = _pick_target(context.opponent_last_message)
        content = template.replace("{strongest_claim}", target)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason=f"targeting {'data-driven' if _DATA_SIGNAL.search(target) else 'longest'} claim",
            content=content,
        )
