from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_TRIGGER = "socratic"
_DEFAULT_INTRO = "Challenge opponent's assumptions{target} with probing questions."
_DEFAULT_QUESTIONS = [
    "What evidence supports...?",
    "How do you explain...?",
    "What are the consequences if you are wrong?",
]

_CERTAINTY_SIGNAL = re.compile(
    r"\b(?:definitely|certainly|undoubtedly|inevitably|always|never|all|none|"
    r"every|no one|everyone|impossible|guaranteed)\b",
    re.I,
)
_CLAIM_SIGNAL = re.compile(
    r"\b(?:therefore|thus|hence|it follows|this proves|this shows|must be|"
    r"clearly shows|demonstrates that)\b",
    re.I,
)


class SocraticSkill(BaseSkill):
    name = "socratic"
    description = "Generates Socratic questioning approach targeting opponent's specific claim"

    def score(self, context: SkillContext) -> float:
        cfg = self._get_config()
        trigger = cfg.get("skill_type_trigger", _DEFAULT_TRIGGER)
        msg = context.opponent_last_message
        s = 0.75 if context.skill_type == trigger else 0.15
        if _CERTAINTY_SIGNAL.search(msg):
            s += 0.20
        if _CLAIM_SIGNAL.search(msg):
            s += 0.15
        if msg.count("?") >= 2:
            s -= 0.15  # opponent already questioning; switch approach
        if context.round_num <= 1:
            s -= 0.30  # no opponent position established yet
        return min(1.0, max(0.0, s))

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        target = (
            f" their claim: '{context.opponent_last_message[:80].strip()}'"
            if context.opponent_last_message else ""
        )
        intro = cfg.get("intro", _DEFAULT_INTRO).replace("{target}", target)
        questions = cfg.get("question_templates", _DEFAULT_QUESTIONS)
        content = intro + " Use " + ", ".join(f"'{q}'" for q in questions)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason="skill_type matches trigger",
            content=content,
        )
