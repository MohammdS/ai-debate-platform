from __future__ import annotations

import json
import re

from src.services.base_agent import get_agent_prompt
from src.shared.config import ConfigManager

_cfg = ConfigManager()

MAX_WORDS: int = _cfg.get_value("debate", "judge_max_words", 200)
MAX_TRANSCRIPT_ENTRIES: int = _cfg.get_value("debate", "judge_max_transcript_entries", 20)

WIN_RE = [re.compile(p, re.I) for p in [
    r"winner\s*:\s*(pro|contra)\b",           # WINNER: Pro  (text or after JSON)
    r'"winner"\s*:\s*"(pro|contra)"',          # "winner": "Pro"  (JSON field)
    r"\b(pro|contra)\s+wins?\b",
    r"winner\s+is\s+(pro|contra)\b",
    r"declare\s+(pro|contra)\s+the\s+winner",
    r"\b(pro|contra)\s+(?:side|debater)\s+wins?\b",
]]
_MAX_WORDS = MAX_WORDS
_MAX_TRANSCRIPT_ENTRIES = MAX_TRANSCRIPT_ENTRIES

CLARIFY_PROMPT = (
    "Your verdict is missing the required WINNER declaration. "
    "Append one line in EXACTLY this format — no extra words:\n"
    "WINNER: Pro\nor\nWINNER: Contra"
)

# (field, max_score) — 3×20 + 4×10 = 100
_SCORE_FIELDS: tuple[tuple[str, int], ...] = (
    ("logic",            20),
    ("evidence",         20),
    ("rebuttal_quality", 20),
    ("relevance",        10),
    ("clarity",          10),
    ("citation_quality", 10),
    ("consistency",      10),   # 10 = no repetition, 0 = very repetitive
)

_JSON_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)\s*```", re.I)


def build_verdict_schema() -> dict:
    """Return a template dict representing the expected JSON verdict structure."""
    side: dict = {f: 0 for f, _ in _SCORE_FIELDS}
    side["total"] = 0
    return {
        "scores": {"pro": dict(side), "contra": dict(side)},
        "reasoning": {"pro": "explanation", "contra": "explanation"},
        "winner": "Pro or Contra",
    }


def parse_structured_verdict(text: str) -> dict | None:
    """Try to extract a structured verdict dict from *text*.

    Attempts (1) full-text JSON parse, then (2) ```json...``` code block.
    Returns None on failure (graceful degradation).
    """
    # Attempt 1: full text
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    # Attempt 2: fenced code block
    m = _JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def format_verdict_for_display(verdict_dict: dict) -> str:
    """Format a structured verdict dict as a human-readable scorecard."""
    lines: list[str] = ["=== JUDGE VERDICT ==="]
    scores = verdict_dict.get("scores", {})
    reasoning = verdict_dict.get("reasoning", {})
    for side in ("pro", "contra"):
        s = scores.get(side, {})
        total = s.get("total", 0)
        lines.append(f"\n{side.upper()}  —  {total}/100")
        lines.append("  " + "─" * 30)
        for field, max_val in _SCORE_FIELDS:
            val = s.get(field, 0)
            label = field.replace("_", " ").title()
            lines.append(f"  {label:<20} {val:>2}/{max_val}")
        r = reasoning.get(side, "")
        if r:
            lines.append(f"  Reasoning: {r}")
    lines.append(f"\n{'═'*36}")
    lines.append(f"  WINNER: {verdict_dict.get('winner', 'Unknown').upper()}")
    lines.append("═" * 36)
    return "\n".join(lines)


def build_system_prompt() -> str:
    cfg = get_agent_prompt("judge")
    criteria = "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}"
        for k, v in cfg.get("scoring_criteria", {}).items()
    )
    rules = "\n".join(f"- {r}" for r in cfg.get("rules", []))
    return (
        f"{cfg.get('system', '')}\n\n"
        "At the end of the debate you issue a final verdict using EXACTLY this format:\n\n"
        f"{cfg.get('verdict_format', '')}\n\nRULES FOR SCORING:\n{criteria}\n{rules}"
        "\n- Penalize named sources that are unsupported, vague, invented, or unverifiable."
        "\n- Penalize factual mistakes even when the speaker names a source."
        "\n- Do not reward a source name unless the claim is plausible and attribution is specific."
        "\n- Penalize hallucinated citations, unsupported numbers, repeated phrases, topic drift,"
        " and failure to answer the previous argument."
        "\n- When possible, respond with valid JSON matching the verdict schema."
    )
