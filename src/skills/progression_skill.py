"""ProgressionSkill — ensures each round introduces a fresh argument angle.

Cycles deterministically through a list of angles keyed by round number.
Activates from round 2 onwards so the opening statement is unconstrained.
All angles and the template are configurable in config/skills_prompts.json.
"""
from __future__ import annotations

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

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

    def can_handle(self, context: SkillContext) -> bool:
        """Activate from round 2 onwards; let round 1 be a free opening."""
        return context.round_num >= 2

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
