"""Post-generation filter that hedges or removes unverifiable factual claims.

Deterministic regex rewrites — no LLM call.  Loaded once at module level.

Patterns are deliberately domain-neutral so the filter works for any debate topic
(science, technology, economics, policy, ethics, etc.).  They target the most
common hallucination shapes seen in debate transcripts:

  • Precise decimal percentage claims ("47.3% of X") — almost always invented
  • Non-round percentage claims attached to "of" ("92% of jobs will be lost")
  • Year-attributed study/report citations ("a 2021 MIT study found…") — very
    frequently fabricated by language models even when no such paper exists
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

_log = logging.getLogger(__name__)

# ── config (skills_prompts.json → "fact_safety") ─────────────────────────────
_PROMPTS_PATH = Path(__file__).resolve().parents[2] / "config" / "skills_prompts.json"


def _load_cfg() -> dict:
    try:
        return json.loads(_PROMPTS_PATH.read_text()).get("fact_safety", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_CFG: dict = _load_cfg()

# ── rewrite rules: (compiled_pattern, replacement_string) ────────────────────
# Rules are applied in order; later rules may refine earlier ones.
# All patterns are domain-neutral — no sports, politics, or cultural specifics.
_RULES: list[tuple[re.Pattern, str]] = [
    # Precise decimal percentage claims: "47.3% of X", "73.4% adoption rate"
    # LLMs frequently invent these; decimal precision signals fabrication.
    (
        re.compile(r"\b\d+\.\d+\s*%"),
        "a significant percentage",
    ),
    # Non-round percentage claims attached to "of": "92% of jobs", "83% of users"
    # Round/half values (50%, 100%) are left alone — they may be intentional.
    (
        re.compile(r"\b(?!(?:50|100)\b)\d+\s*%\s+of\b"),
        "a significant portion of",
    ),
    # Year-attributed study/report/survey/paper citations:
    # "a 2021 study by Harvard", "the 2019 MIT report found", etc.
    # This is a hallucination hotspot across all domains.
    (
        re.compile(
            r"\b(?:a|the)\s+20\d{2}\s+(?:study|report|survey|research|paper)\b",
            re.I,
        ),
        "recent research",
    ),
]


class FactSafetyFilter:
    """Apply regex rewrites to hedge unverifiable factual claims in generated text."""

    def clean(self, text: str, has_web_evidence: bool = False) -> str:
        """Return *text* with unsafe claim patterns hedged.

        Returns the original string unchanged if ``fact_safety.enabled`` is
        ``false`` in ``config/skills_prompts.json`` or current web evidence
        was included in the prompt for the response.
        """
        if has_web_evidence or not _CFG.get("enabled", True):
            return text

        result = text
        rewrites = 0
        for pattern, replacement in _RULES:
            new = pattern.sub(replacement, result)
            if new != result:
                rewrites += 1
                result = new

        if rewrites:
            _log.info(
                "[fact_safety] %d rewrite(s) applied — hedged unverifiable claims",
                rewrites,
            )
        return result
