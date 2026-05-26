from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_INSTRUCTION = "Be direct and assertive. Avoid aggressive language. No personal attacks."

_AGGRESSION_SIGNAL = re.compile(
    r"\b(?:ridiculous|absurd|nonsense|idiotic|pathetic|laughable|"
    r"completely wrong|total failure|blatantly|you clearly|how can you)\b",
    re.I,
)
_FORMAL_SIGNAL = re.compile(
    r"\b(?:respectfully|I acknowledge|to be fair|I concede|one must consider|"
    r"with respect|I appreciate your point)\b",
    re.I,
)


class ToneModerationSkill(BaseSkill):
    name = "tone_moderation"
    description = "Ensures assertive but respectful tone"

    def score(self, context: SkillContext) -> float:
        msg = context.opponent_last_message
        own_last = next(
            (e["content"] for e in reversed(context.transcript) if e.get("role") == "assistant"),
            "",
        )
        s = 0.50
        if _AGGRESSION_SIGNAL.search(msg):
            s += 0.30
        if _AGGRESSION_SIGNAL.search(own_last):
            s += 0.25
        if _FORMAL_SIGNAL.search(own_last):
            s -= 0.15
        return max(0.15, min(1.0, s))

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        content = cfg.get("instruction", _DEFAULT_INSTRUCTION)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="always applicable",
            content=content,
        )
