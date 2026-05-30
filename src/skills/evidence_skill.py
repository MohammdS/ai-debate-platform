from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_TRIGGER = "evidence_based"
_DEFAULT_TEMPLATE = (
    "Support your argument{topic_hint} with concrete facts, data, or "
    "widely recognised evidence. Cite the source or institution behind "
    "each claim. Avoid invented statistics."
)

_STAT_SIGNAL = re.compile(
    r"\d+(?:\.\d+)?\s*%|"
    r"\b\d+\s+(?:billion|million|trillion)\b|"
    r"\b(?:study|research|data|statistics|figures|numbers|survey|report)\b",
    re.I,
)
_ANECDOTE_SIGNAL = re.compile(
    r"\b(?:personally|in my experience|I have seen|people I know|a friend|anecdotally)\b",
    re.I,
)


class EvidenceSkill(BaseSkill):
    name = "evidence"
    description = "Suggests evidence-based framing for the argument"

    def score(self, context: SkillContext) -> float:
        cfg = self._get_config()
        trigger = cfg.get("skill_type_trigger", _DEFAULT_TRIGGER)
        if context.skill_type == trigger:
            s = 0.75
        else:
            s = 0.20
            if _STAT_SIGNAL.search(context.opponent_last_message):
                s += 0.30  # opponent cited stats; counter with evidence even cross-type
        own_last = next(
            (e["content"] for e in reversed(context.transcript) if e.get("role") == "assistant"),
            "",
        )
        if _ANECDOTE_SIGNAL.search(own_last):
            s += 0.15
        return min(1.0, max(0.0, s))

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
