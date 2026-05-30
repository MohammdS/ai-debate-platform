"""RepetitionGuardSkill — prevents debaters from recycling previous arguments.

Reads the debater's own past turns (role == "assistant" entries in the
transcript) and injects a "do NOT repeat" reminder listing the opening
phrase of each recent argument.  Fully deterministic — no LLM call.
"""
from __future__ import annotations

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_MAX_TRACKED = 3
_DEFAULT_TEMPLATE = (
    "PREVIOUSLY ARGUED — do NOT repeat or rephrase these points:\n{phrases}\n"
    "You MUST introduce a genuinely new idea this turn."
)
_ROUND1_FALLBACK = (
    "First-turn baseline: choose a distinct angle now and avoid reusing this framing "
    "in later rounds."
)


class RepetitionGuardSkill(BaseSkill):
    name = "repetition_guard"
    description = "Prevents the debater from repeating arguments made in earlier rounds"

    def score(self, context: SkillContext) -> float:
        own = [e for e in context.transcript if e.get("role") == "assistant"]
        if not own:
            return 0.0
        s = 0.45
        if len(own) >= 3:
            s += 0.10
        if len(own) >= 5:
            s += 0.05
        if context.round_num >= 4:
            s += 0.08
        return min(0.68, s)

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        max_track = cfg.get("max_previous_tracked", _DEFAULT_MAX_TRACKED)
        template = cfg.get("template", _DEFAULT_TEMPLATE)

        own = [e for e in context.transcript if e.get("role") == "assistant"]
        if not own:
            return SkillResult(
                skill_name=self.name,
                selected=True,
                reason="first-turn anti-repetition baseline",
                content=_ROUND1_FALLBACK,
            )
        recent = own[-max_track:]

        phrases: list[str] = []
        for entry in recent:
            content = entry.get("content", "").strip()
            # Extract the first meaningful sentence as a fingerprint.
            for chunk in content.split("."):
                chunk = chunk.strip()
                if len(chunk) > 15:
                    phrases.append(chunk[:100])
                    break

        if not phrases:
            return SkillResult(
                skill_name=self.name,
                selected=False,
                reason="no extractable argument phrases",
                content="",
            )

        bulleted = "\n".join(f"- {p}" for p in phrases)
        content = template.replace("{phrases}", bulleted)
        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason=f"blocking repetition of {len(phrases)} prior argument(s)",
            content=content,
        )
