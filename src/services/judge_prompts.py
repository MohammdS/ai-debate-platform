from __future__ import annotations

import contextlib
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

# Score fields and their maximum values — loaded from config/skills.json so
# weights can be tuned without touching source code.
# Fallback keeps the original 3×20 + 4×10 = 100 scheme if config is absent.
_SCORE_FIELDS_FALLBACK: tuple[tuple[str, int], ...] = (
    ("logic",            20),
    ("evidence",         20),
    ("rebuttal_quality", 20),
    ("relevance",        10),
    ("clarity",          10),
    ("citation_quality", 10),
    ("consistency",      10),
)
_raw_score_fields: dict = get_agent_prompt("judge").get("score_fields", {})
_SCORE_FIELDS: tuple[tuple[str, int], ...] = (
    tuple((k, int(v)) for k, v in _raw_score_fields.items())
    if _raw_score_fields
    else _SCORE_FIELDS_FALLBACK
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


_FIELD_MAX: dict[str, int] = dict(_SCORE_FIELDS)


def _validate_scores(verdict: dict) -> dict:
    """Clamp every score to [0, max], recompute totals, return corrected dict."""
    scores = verdict.get("scores", {})
    for side in ("pro", "contra"):
        s = scores.get(side, {})
        if not isinstance(s, dict):
            scores[side] = s = {}
        total = 0
        for field, mx in _SCORE_FIELDS:
            val = s.get(field, 0)
            try:
                val = int(val)
            except (TypeError, ValueError):
                val = 0
            val = max(0, min(val, mx))
            s[field] = val
            total += val
        s["total"] = total          # always recompute — never trust the LLM's arithmetic
    return verdict


def parse_structured_verdict(text: str) -> dict | None:
    """Try to extract a structured verdict dict from *text*.

    Attempts (1) full-text JSON parse, then (2) ```json...``` code block.
    Scores are clamped to their declared maximums and totals are recomputed.
    Returns None on failure (graceful degradation).
    """
    raw: dict | None = None
    try:
        raw = json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        m = _JSON_BLOCK_RE.search(text)
        if m:
            with contextlib.suppress(json.JSONDecodeError, ValueError):
                raw = json.loads(m.group(1))
    return _validate_scores(raw) if raw is not None else None


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

    penalization = "\n".join(
        f"  {i + 1}. {item}"
        for i, item in enumerate(cfg.get("penalization_criteria", []))
    )
    additional = "\n".join(f"- {r}" for r in cfg.get("additional_scoring_rules", []))
    reasoning = "\n".join(f"- {r}" for r in cfg.get("reasoning_rules", []))

    return (
        f"{cfg.get('system', '')}\n\n"
        "At the end of the debate you issue a final verdict using EXACTLY this format:\n\n"
        f"{cfg.get('verdict_format', '')}\n\n"
        f"RULES FOR SCORING:\n{criteria}\n{rules}\n\n"
        f"MANDATORY PENALIZATION CRITERIA — deduct points for ALL of the following:\n{penalization}\n\n"
        f"ADDITIONAL SCORING RULES:\n{additional}\n\n"
        f"CRITICAL — REASONING SECTION RULES:\n{reasoning}\n"
        "- When possible, respond with valid JSON matching the verdict schema."
    )
