"""Post-generation filter that hedges or removes unverifiable factual claims.

Deterministic regex rewrites — no LLM call.  Loaded once at module level.

Patterns target the most common hallucination shapes seen in debate transcripts:
  • Inflated award-winner counts ("17 Ballon d'Or winners")
  • Made-up percentage claims ("92% of jobs will be automated")
  • Unverifiable "FIFA named / ranked / voted" superlative claims
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
_RULES: list[tuple[re.Pattern, str]] = [
    # "17 Ballon d'Or winners/titles" — LLMs routinely invent these numbers.
    # Real per-club counts are ≤ 8; any specific count risks being wrong.
    (
        re.compile(r"\b\d+\s+[Bb]allon\s+d['’][Oo]r\b"),
        "multiple Ballon d'Or",
    ),
    # Percentage claims attached to "of": "92% of jobs", "73.4% of users"
    # Round/half values (50%, 100%) are left alone — they may be intentional.
    (
        re.compile(r"\b(?!(?:50|100)\b)\d+\.?\d*\s*%\s+of\b"),
        "a significant portion of",
    ),
    # "FIFA named / ranked / voted / selected X the best / #1"
    # The underlying award often doesn't exist or is misattributed.
    (
        re.compile(r"\bFIFA\s+(?:named|ranked|voted|selected|awarded)\b", re.I),
        "reportedly FIFA",
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
