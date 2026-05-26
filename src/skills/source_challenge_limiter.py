"""SourceChallengeLimiter — per-debater stateful gate for source challenges.

Counts actual debater turns since the last source-challenge directive was
issued.  More accurate than round-number-based throttling because it tracks
the real cadence of challenges per agent rather than global round parity.

Lifecycle (called from Debater._build_skill_guidance):
    1. limiter.record_turn()          — one call per debater turn
    2. allow = limiter.should_allow() — True every ``interval`` turns
    3. pass allow into SkillContext.metadata["allow_source_challenge"]
    4. CitationSkill reads the flag and gates the challenge directive
    5. limiter.record_challenge()     — reset counter when challenge emitted
"""
from __future__ import annotations

_DEFAULT_INTERVAL = 3   # minimum debater turns between source challenges


class SourceChallengeLimiter:
    """Stateful per-debater throttle for source-challenge directives.

    Initialises with ``_turns_since_challenge == interval`` so the very
    first eligible turn allows a challenge immediately (no warm-up silence).
    """

    def __init__(self, interval: int = _DEFAULT_INTERVAL) -> None:
        self._interval: int = max(1, interval)
        # Pre-charge so turn 1 is eligible.
        self._turns_since_challenge: int = self._interval

    # ── public API ────────────────────────────────────────────────────────

    def record_turn(self) -> None:
        """Increment the turns-since-challenge counter.

        Call once at the start of every debater turn, before should_allow().
        """
        self._turns_since_challenge += 1

    def should_allow(self) -> bool:
        """Return True if enough turns have passed since the last challenge."""
        return self._turns_since_challenge >= self._interval

    def record_challenge(self) -> None:
        """Reset counter after a challenge directive has been issued."""
        self._turns_since_challenge = 0

    # ── read-only properties ──────────────────────────────────────────────

    @property
    def turns_since_last(self) -> int:
        """Turns elapsed since the last challenge (or since construction)."""
        return self._turns_since_challenge

    @property
    def interval(self) -> int:
        """Configured minimum turns between challenges."""
        return self._interval
