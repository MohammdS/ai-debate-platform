"""DebateMemory — compact per-debater memory of the debate so far.

Tracks:
- pro_claims: deque of opening-phrase fingerprints from Pro's turns
- contra_claims: deque of opening-phrase fingerprints from Contra's turns
- used_evidence: set of evidence snippets already cited
- used_urls: set of URLs already fetched by web search
- repeated_phrases: phrases detected as repeated across turns

Fully deterministic — no LLM calls. Used by ContextCompressor to
enrich the prompt with structured anti-repetition context.
"""
from __future__ import annotations

import re
from collections import deque

_FINGERPRINT_CHARS = 80
_MIN_PHRASE_LEN = 15
_MAX_TRACKED = 5


class DebateMemory:
    """Compact structured memory of a running debate."""

    def __init__(self) -> None:
        self.pro_claims: deque[str] = deque(maxlen=_MAX_TRACKED)
        self.contra_claims: deque[str] = deque(maxlen=_MAX_TRACKED)
        self.used_evidence: set[str] = set()
        self.used_urls: set[str] = set()
        self.repeated_phrases: list[str] = []
        self._seen_fingerprints: set[str] = set()

    def record_turn(self, speaker: str, content: str) -> None:
        """Record a debater turn. speaker must be 'pro' or 'contra'."""
        fingerprint = self._fingerprint(content)
        if not fingerprint:
            return

        fp_key = fingerprint.lower()[:60]
        if fp_key in self._seen_fingerprints:
            self.repeated_phrases.append(fingerprint)
        else:
            self._seen_fingerprints.add(fp_key)

        target = self.pro_claims if speaker.lower() == "pro" else self.contra_claims
        target.append(fingerprint)  # deque(maxlen=_MAX_TRACKED) handles eviction

        self.used_evidence.update(self._extract_evidence_markers(content))

    def get_memory_block(self, for_speaker: str) -> str:
        """Return a formatted memory block to inject into the prompt."""
        lines: list[str] = []

        own = self.pro_claims if for_speaker.lower() == "pro" else self.contra_claims
        opp = self.contra_claims if for_speaker.lower() == "pro" else self.pro_claims

        if own:
            bullets = "\n".join(f"  - {c[:70]}" for c in list(own)[-3:])
            lines.append(f"YOUR PREVIOUS CLAIMS (do NOT repeat):\n{bullets}")

        if opp:
            bullets = "\n".join(f"  - {c[:70]}" for c in list(opp)[-3:])
            lines.append(f"OPPONENT'S CLAIMS (address these directly):\n{bullets}")

        if self.repeated_phrases:
            bullets = "\n".join(f"  - {p[:60]}" for p in self.repeated_phrases[-2:])
            lines.append(f"DETECTED REPETITION (avoid these phrases):\n{bullets}")

        if self.used_evidence:
            bullets = "\n".join(f"  - {e[:60]}" for e in list(self.used_evidence)[:4])
            lines.append(f"ALREADY CITED EVIDENCE (do not reuse without attribution):\n{bullets}")

        return "\n\n".join(lines)

    def register_urls(self, urls: list[str]) -> None:
        """Record URLs returned by a web search so they are not re-fetched."""
        self.used_urls.update(urls)

    def repetition_count(self) -> int:
        """Return total detected repetitions."""
        return len(self.repeated_phrases)

    @staticmethod
    def _fingerprint(content: str) -> str:
        """Extract first meaningful sentence as a fingerprint."""
        for chunk in content.split("."):
            chunk = chunk.strip()
            if len(chunk) >= _MIN_PHRASE_LEN:
                return chunk[:_FINGERPRINT_CHARS]
        return ""

    @staticmethod
    def _extract_evidence_markers(content: str) -> set[str]:
        """Extract patterns that look like cited evidence."""
        markers: set[str] = set()
        for m in re.finditer(r'\d+\s*%[^.]{0,40}', content):
            markers.add(m.group().strip()[:50])
        for m in re.finditer(r'(?:study|research|report|found|shows?)\s+[^.]{10,50}', content, re.I):
            markers.add(m.group().strip()[:50])
        return markers
