"""ProgressionSkill — ensures each round introduces a fresh argument angle.

Cycles deterministically through a list of angles keyed by round number.
Activates from round 2 onwards so the opening statement is unconstrained.
All angles and the template are configurable in config/skills_prompts.json.
"""
from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_REPETITION_SIGNAL = re.compile(
    r"\b(?:as I (?:said|mentioned|argued|noted)|once again|reiterating|to repeat|as previously)\b",
    re.I,
)
_DEEP_DIVE_SIGNAL = re.compile(
    r"\b(?:furthermore|in addition|building on|expanding on|another aspect|additionally)\b",
    re.I,
)

_DEFAULT_ANGLES = [
    "economic and financial impact",
    "historical precedent and track record",
    "a specific counterexample that undermines the opponent",
    "long-term consequences and sustainability",
    "ethical, social, or cultural dimension",
]

_DEFAULT_TEMPLATE = (
    "Round {round_num}: You MUST introduce a FRESH perspective. "
    "Explore the **{angle}** of this debate — an angle not yet fully addressed. "
    "Do not recycle previous arguments."
)


class ProgressionSkill(BaseSkill):
    name = "progression"
    description = "Pushes debaters to introduce a new argument angle each round"

    def score(self, context: SkillContext) -> float:
        if context.round_num < 2:
            return 0.0
        own_last = next(
            (e["content"] for e in reversed(context.transcript) if e.get("role") == "assistant"),
            "",
        )
        s = 0.55
        if _REPETITION_SIGNAL.search(own_last):
            s += 0.25
        if context.round_num >= 6:
            s += 0.15
        if context.round_num == 2:
            s += 0.10
        if _DEEP_DIVE_SIGNAL.search(own_last):
            s -= 0.15
        return min(1.0, max(0.0, s))

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        angles = cfg.get("angles", _DEFAULT_ANGLES)
        template = cfg.get("template", _DEFAULT_TEMPLATE)

        # Deterministic rotation: (round_num - 1) maps round 2→index 0, etc.
        angle = angles[(context.round_num - 1) % len(angles)]
        content = (
            template
            .replace("{round_num}", str(context.round_num))
            .replace("{angle}", angle)
        )
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason=f"round {context.round_num} — fresh angle: {angle}",
            content=content,
        )
