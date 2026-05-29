"""Tests for src/services/debater_prompts.py — prompt content and policy checks.

Covers:
 1.  System prompt contains assigned stance
 2.  System prompt contains opponent stance
 3.  Per-turn compressed context contains opponent's last turn
 4.  Per-turn compressed context contains debate memory (summary / used angles)
 5.  Turn header contains topic, stance, and opponent stance
 6.  Turn header is injected into compressed context
 7.  System prompt contains fact-safety rules
 8.  No instruction to invent citations in debater or judge prompts
 9.  Judge prompt penalises hallucinated/unsupported sources
10.  Judge prompt explicitly covers all 5 required penalisation categories
11.  STYLE_POLICY forbids aggressive language
12.  RESPONSE_STRUCTURE contains all 4 required parts
13.  Regression: sample transcript with hallucinated source — judge prompt must
     include rules that would penalise it
"""
from __future__ import annotations

import pytest

from src.services.context_compressor import ContextCompressor
from src.services.debater_prompts import (
    RESPONSE_STRUCTURE,
    STYLE_POLICY,
    build_system_prompt,
    build_turn_header,
)
from src.services.judge_prompts import build_system_prompt as build_judge_prompt

# ── 1. System prompt contains the assigned stance ────────────────────────────

def test_system_prompt_contains_assigned_stance():
    prompt = build_system_prompt(
        "Debater A", "The internet improves democracy",
        "The internet strengthens democratic participation",
        "The internet undermines democratic participation",
    )
    assert "The internet strengthens democratic participation" in prompt


# ── 2. System prompt contains the opponent stance ────────────────────────────

def test_system_prompt_contains_opponent_stance():
    prompt = build_system_prompt(
        "Debater B", "The internet improves democracy",
        "The internet undermines democratic participation",
        "The internet strengthens democratic participation",
    )
    assert "The internet strengthens democratic participation" in prompt


# ── 3. Compressed per-turn context includes the opponent's latest turn ────────

def test_turn_context_contains_opponent_last_turn():
    compressor = ContextCompressor()
    opponent_text = "Automation creates more jobs than it destroys over the long run."
    history = [{"role": "user", "content": opponent_text}]
    messages = compressor.compress(history, "System prompt")
    assert opponent_text in messages[1]["content"]


# ── 4. Compressed per-turn context includes debate memory ────────────────────

def test_turn_context_contains_debate_memory():
    """When there are prior turns, the compressor injects a DEBATE SO FAR or
    ALREADY ARGUED block that constitutes the compact memory."""
    compressor = ContextCompressor()
    history = [
        {"role": "assistant", "content": "Renewable energy creates long-term economic stability."},
        {"role": "user",      "content": "Fossil fuels remain cheaper in the short term."},
    ]
    messages = compressor.compress(history, "System prompt")
    user_content = messages[1]["content"]
    # At least one memory block must be present
    assert "DEBATE SO FAR" in user_content or "ALREADY ARGUED" in user_content


# ── 5. Turn header contains topic, assigned stance, opponent stance ───────────

def test_turn_header_contains_all_three_context_items():
    topic = "Universal basic income is beneficial"
    stance = "UBI reduces poverty and increases freedom"
    opponent = "UBI is unaffordable and reduces work incentives"
    header = build_turn_header(topic, stance, opponent)
    assert topic    in header
    assert stance   in header
    assert opponent in header


# ── 6. Turn header is injected at the top of the compressed user message ──────

def test_turn_header_appears_in_compressed_context():
    compressor = ContextCompressor()
    history = [{"role": "user", "content": "Some opponent argument."}]
    header = build_turn_header(
        "Nuclear energy is safe",
        "Nuclear is our safest energy source",
        "Nuclear poses unacceptable safety risks",
    )
    messages = compressor.compress(history, "System prompt", turn_header=header)
    user_content = messages[1]["content"]
    assert header in user_content
    # Turn header should precede the opponent's message in the content
    assert user_content.index(header) < user_content.index("Some opponent argument.")


# ── 7. System prompt contains fact-safety rules ───────────────────────────────

def test_system_prompt_contains_fact_safety_rules():
    prompt = build_system_prompt(
        "Pro", "Gene editing should be regulated",
        "Gene editing requires strict oversight",
        "Gene editing should be freely permitted",
    )
    # FACT_SAFETY_POLICY is embedded verbatim — key phrase must appear
    assert "FACT-SAFETY" in prompt
    assert "NEVER invent" in prompt


# ── 8. No instruction to invent citations in any prompt ──────────────────────

@pytest.mark.parametrize("prompt_text", [
    build_system_prompt("Pro", "T", "A", "B"),
    build_judge_prompt(),
])
def test_no_instruction_to_invent_citations(prompt_text: str):
    """Neither debater nor judge prompts should instruct the model to fabricate sources."""
    lower = prompt_text.lower()
    assert "you must invent"      not in lower
    assert "make up sources"      not in lower
    assert "fabricate citations"  not in lower
    assert "create fake"          not in lower


# ── 9. Judge prompt penalises hallucinated / unsupported sources ──────────────

def test_judge_prompt_penalises_hallucinated_sources():
    judge_prompt = build_judge_prompt()
    lower = judge_prompt.lower()
    # Must contain at least one of these penalisation terms
    assert (
        "hallucinated" in lower
        or "fake citation" in lower
        or "invented" in lower
        or "unsupported" in lower
    )


# ── 10. Judge prompt covers all 5 required penalisation categories ─────────────

def test_judge_prompt_covers_five_penalisation_categories():
    """Judge prompt must address: repetition, fake citations, drift,
    unsupported precise claims, and weak rebuttals."""
    judge_prompt = build_judge_prompt()
    lower = judge_prompt.lower()

    assert "repetition" in lower or "repeat" in lower,         "missing: repetition"
    assert (
        "hallucinated" in lower or "fake" in lower or "invented" in lower
    ),                                                          "missing: fake citations"
    assert "drift" in lower or "relevance" in lower,           "missing: irrelevant drift"
    assert "unsupported" in lower or "unverifiable" in lower,  "missing: unsupported claims"
    assert "rebuttal" in lower,                                 "missing: weak rebuttals"


# ── 11. STYLE_POLICY promotes confrontational, winning-focused language ───────

def test_style_policy_promotes_confrontational_language():
    lower = STYLE_POLICY.lower()
    # Must encourage fighting to win, not diplomatic hedging
    assert "win" in lower or "bold" in lower or "sharp" in lower
    # Must forbid weak hedging phrases
    assert "one might argue" in lower or "perhaps" in lower or "diplomatic" in lower \
        or "hedging" in lower


# ── 12. RESPONSE_STRUCTURE defines all 4 required parts ──────────────────────

def test_response_structure_has_four_parts():
    """RESPONSE_STRUCTURE uses numbered natural-prose guidelines (no bold headers)."""
    lower = RESPONSE_STRUCTURE.lower()
    # 1. open hard / lead with strongest point
    assert "immediately" in lower or "strongest point" in lower or "hit hard" in lower, \
        "missing: instruction to open with strongest point"
    # 2. expose flaw / challenge the previous point
    assert "expose" in lower or "flaw" in lower or "wrong" in lower or "challenge" in lower, \
        "missing: instruction to challenge previous point"
    # 3. evidence or reasoning
    assert "evidence" in lower, "missing: evidence / reasoning"
    # 4. closing sentence
    assert "close with" in lower or "closing" in lower or "knockout" in lower, \
        "missing: closing instruction"
    # must NOT instruct bold headers (format is natural prose)
    assert "**rebuttal:**" not in lower, "old bold-header format still present"


# ── 13. Regression: hallucinated-source transcript — judge must penalise ──────

def test_regression_judge_penalises_hallucinated_sources_in_transcript():
    """
    Regression scenario: a debater claims
      'According to a 2021 Stanford study, renewable energy reduces costs by 73.4%'
    — a hallucinated specific citation.  The judge system prompt must contain
    explicit rules that would penalise this pattern.
    """
    judge_prompt = build_judge_prompt()
    lower = judge_prompt.lower()

    # The judge must penalise fabricated citations
    assert "hallucinated" in lower or "unsupported" in lower, (
        "Judge prompt missing penalty rule for hallucinated citations"
    )
    # The judge must penalise unsupported precise numeric claims
    assert (
        "unsupported" in lower
        or "unverifiable" in lower
        or "specific" in lower
    ), "Judge prompt missing penalty rule for unsupported precise claims"
    # The judge must penalise under Citation Quality or Evidence
    assert "citation" in lower, (
        "Judge prompt missing Citation Quality penalisation category"
    )
    # Explicit penalise/penalize wording must appear
    assert "penali" in lower, (
        "Judge prompt never uses 'penalise'/'penalize' — penalties unclear"
    )


# ── 14. FactSafetyFilter patterns are domain-neutral ─────────────────────────

def test_fact_safety_filter_is_domain_neutral():
    """The filter must not contain sport-specific patterns (FIFA, Ballon d'Or)."""
    import inspect

    from src.skills import fact_safety_filter
    source = inspect.getsource(fact_safety_filter)
    assert "FIFA"          not in source, "sports-specific FIFA pattern found"
    assert "Ballon"        not in source, "sports-specific Ballon d'Or pattern found"
    assert "ballon"        not in source, "sports-specific ballon pattern found"


def test_fact_safety_filter_hedges_decimal_percentage():
    """Precise decimal percentages are hedged regardless of topic domain."""
    from src.skills.fact_safety_filter import FactSafetyFilter
    f = FactSafetyFilter()
    hedged = f.clean("Automation will eliminate 47.3% of current jobs within a decade.")
    assert "47.3%" not in hedged
    assert "significant percentage" in hedged or "significant" in hedged


def test_fact_safety_filter_hedges_year_attributed_study():
    """Year-attributed study citations are hedged to 'recent research'."""
    from src.skills.fact_safety_filter import FactSafetyFilter
    f = FactSafetyFilter()
    hedged = f.clean("A 2021 study by Oxford found that universal income reduces anxiety.")
    assert "2021" not in hedged or "recent research" in hedged


def test_fact_safety_filter_passes_through_with_web_evidence():
    """Filter is bypassed when has_web_evidence=True."""
    from src.skills.fact_safety_filter import FactSafetyFilter
    f = FactSafetyFilter()
    original = "A 2021 study by Harvard found that 47.3% of workers prefer remote work."
    result = f.clean(original, has_web_evidence=True)
    assert result == original


# ── 15. System prompt word-limit range appears in prompt ─────────────────────

def test_system_prompt_states_word_limit_range():
    prompt = build_system_prompt("Pro", "T", "A", "B", word_min=80, word_max=130)
    assert "80" in prompt and "130" in prompt
