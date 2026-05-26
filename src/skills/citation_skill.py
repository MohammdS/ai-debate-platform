"""CitationSkill — reminds debaters to cite sources; limits source-challenges.

Fix: the challenge directive ("demand they name their source") is now gated
to fire at most once every ``challenge_interval_rounds`` rounds (default 3).
This prevents the Socratic debater from issuing a source challenge on every
single turn, which stifles debate progression.

The plain citation reminder (instruction) is always emitted; only the
opponent-challenge suffix is rate-limited.
"""
from __future__ import annotations

import re

from src.skills.base_skill import BaseSkill
from src.skills.models import SkillContext, SkillResult

_DEFAULT_INSTRUCTION = "Name your source for every factual claim you make."
_DEFAULT_CHALLENGE_TEMPLATE = (
    " Opponent stated: '{snippet}' — demand they name their source if it lacks one."
)
_DEFAULT_SNIPPET_CHARS = 60
_DEFAULT_CHALLENGE_INTERVAL = 3  # rounds between source challenges

_FACTUAL_CLAIM_SIGNAL = re.compile(
    r"\b(?:according to|study shows|research finds|data shows|scientists say|"
    r"experts agree|statistics show|the evidence|it has been shown)\b|"
    r"\d+(?:\.\d+)?\s*%",
    re.I,
)


class CitationSkill(BaseSkill):
    name = "citation"
    description = "Reminds debater to cite sources; limits source-challenges to every N rounds"

    def score(self, context: SkillContext) -> float:
        s = 0.40
        if _FACTUAL_CLAIM_SIGNAL.search(context.opponent_last_message):
            s += 0.25
        if context.skill_type == "evidence_based":
            s += 0.20
        if context.round_num == 1:
            s -= 0.15
        if context.skill_type == "judge":
            s -= 0.30
        return max(0.10, min(1.0, s))

    def run(self, context: SkillContext) -> SkillResult:
        cfg = self._get_config()
        instruction = cfg.get("instruction", _DEFAULT_INSTRUCTION)
        challenge_tmpl = cfg.get("challenge_template", _DEFAULT_CHALLENGE_TEMPLATE)
        snippet_chars = cfg.get("snippet_chars", _DEFAULT_SNIPPET_CHARS)
        interval = cfg.get("challenge_interval_rounds", _DEFAULT_CHALLENGE_INTERVAL)

        # Rate-limit: issue a source challenge only from round 2 onwards (round 1
        # has no real opponent argument), and only every `interval` rounds after that.
        # Also gated by the per-agent SourceChallengeLimiter when set.
        challenge = ""
        round_qualifies = context.round_num > 1 and (context.round_num - 1) % interval == 0
        meta_allows = context.metadata.get("allow_source_challenge", True)
        challenge_issued = bool(context.opponent_last_message and round_qualifies and meta_allows)
        if challenge_issued:
            snippet = context.opponent_last_message[:snippet_chars].strip()
            challenge = challenge_tmpl.replace("{snippet}", snippet)

        return SkillResult(
            skill_name=self.name,
            selected=True,
            reason=(
                f"source challenge (round {context.round_num}, interval={interval}, meta={meta_allows})"
                if challenge else "citation reminder only"
            ),
            content=instruction + challenge,
            metadata={"source_challenge": challenge_issued},
        )
