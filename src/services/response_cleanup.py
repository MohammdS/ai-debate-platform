from __future__ import annotations

import re
import unicodedata

_SECTION_LABEL_RE = re.compile(
    r"(^|\n|(?<=[.!?])\s+)(?:Rebuttal|New angle|Argument|Response)\s*:\s*",
    re.I,
)

# Normalise curly/smart apostrophes → straight before matching
_APOSTROPHE_RE = re.compile(r"[‘’‚‛′‵]")

_BANNED_PHRASES = (
    "my opponent",
    "opponent conveniently",
    "red herring",
    "shift the focus",       # catches both "let's shift the focus" and "i'd like to shift"
    "you claim",
    "i'd like to",
    "i would like to",
    "let's get down to business",
)
_BANNED_OPENINGS = (
    "the claim that",
    "the assertion that",
    "the opponent's assertion",
    "the opponent's claim",
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
    return _SECTION_LABEL_RE.sub(lambda m: m.group(1), text).strip()


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
