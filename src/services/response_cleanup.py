from __future__ import annotations

import re
import unicodedata

# Strips plain section labels that leak without bold markers.
_SECTION_LABEL_RE = re.compile(
    r"(^|\n|(?<=[.!?])\s+)(?:Rebuttal|New\s+angle|Argument|Response)\s*:\s*",
    re.I,
)

# Strips bold structured headers that the LLM adds from the RESPONSE_STRUCTURE
# prompt (e.g. "**Rebuttal:** …").  The 4-part structure is still enforced by
# the system prompt; the labels are removed here so the transcript reads as
# clean, natural prose.
# Matches "**Label:**" — the LLM places the colon INSIDE the bold markers, so
# the pattern is \*\* + label + : + \*\* (not \*\* + label + \*\* + :).
_BOLD_SECTION_RE = re.compile(
    r"\*\*\s*(?:Rebuttal|New\s+Argument|Evidence\s+or\s+Reasoning|Evidence|Reasoning|Closing)\s*:\s*\*\*\s*",
    re.I,
)

# Normalise curly/smart apostrophes → straight before matching
_APOSTROPHE_RE = re.compile(r"[‘’‚‛′‵]")

_BANNED_PHRASES = (
    "my opponent",
    "the opponent",           # any reference to "the opponent" anywhere in the response
    "opponent conveniently",
    "the claim that",         # stilted rhetorical framing — caught anywhere, not just opening
    "the assertion that",     # same
    "it is asserted that",
    "it is claimed that",
    "overlooks the fact that",  # lazy filler — state the counter-fact directly instead
    "ignores the fact that",    # same
    "fails to acknowledge",
    "red herring",
    "shift the focus",
    "you claim",
    "i'd like to",
    "i would like to",
    "let's get down to business",
)
_BANNED_OPENINGS = (
    # "That claim/argument/assessment [verb]s…" — formulaic rebuttal opener used every turn
    "that claim",
    "that argument",
    "that assessment",
    "that position",
    "that reasoning",
    "that logic",
    "that view",
    "that point",
    "i challenge the opponent",
    "you claim",
    "you argue",
    "this overlooks",
    "a fresh perspective",
    "new argument",
)
_WORD_RE = re.compile(r"[\w']+")


def _normalise(text: str) -> str:
    """Lowercase and replace smart apostrophes with straight ones."""
    return _APOSTROPHE_RE.sub("'", unicodedata.normalize("NFKC", text)).lower()


def strip_debate_labels(text: str) -> str:
    # 1. Strip plain leaked labels ("Rebuttal: …")
    text = _SECTION_LABEL_RE.sub(lambda m: m.group(1), text)
    # 2. Strip bold structured headers ("**Rebuttal:** …")
    text = _BOLD_SECTION_RE.sub("", text)
    return text.strip()


def validate_debate_response(response: str) -> list[str]:
    text = _normalise(response)
    found = [phrase for phrase in _BANNED_PHRASES if phrase in text]
    found.extend(p for p in _BANNED_OPENINGS if text.lstrip().startswith(p))
    return found


def repeated_word_run(response: str, previous: str, max_allowed: int = 5) -> str:
    current = _WORD_RE.findall(response.lower())
    prior = _WORD_RE.findall(previous.lower())
    n = max_allowed + 1
    if len(current) < n or len(prior) < n:
        return ""
    prior_runs = {tuple(prior[i:i + n]) for i in range(len(prior) - n + 1)}
    for i in range(len(current) - n + 1):
        run = tuple(current[i:i + n])
        if run in prior_runs:
            return " ".join(run)
    return ""
