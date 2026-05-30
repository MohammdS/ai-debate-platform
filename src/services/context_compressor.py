"""ContextCompressor — reduces LLM token usage in debate prompts.

Replaces the full multi-turn message history with a single compressed
user message containing exactly:
  1. DEBATE SO FAR   — one-line snippet per recent turn (rolling window)
  2. ALREADY ARGUED  — deduplicated opening phrase of the debater's own turns
  3. OPPONENT'S LAST MESSAGE — the full last opponent message
  4. Skill guidance  — injected verbatim at the end (if any)

Compared with sending the raw transcript this cuts token usage by ~3-5×
for a 10-round debate.  Fully deterministic — no LLM calls.
"""
from __future__ import annotations

_DEFAULT_SNIPPET_CHARS = 80
_DEFAULT_MAX_SUMMARY_TURNS = 6   # rolling window of past turns shown in summary


class ContextCompressor:
    """Build a compressed [system, user] message list for a debater's LLM call."""

    def __init__(
        self,
        snippet_chars: int = _DEFAULT_SNIPPET_CHARS,
        max_summary_turns: int = _DEFAULT_MAX_SUMMARY_TURNS,
    ) -> None:
        self._snippet = snippet_chars
        self._max_turns = max(1, max_summary_turns)

    # ── public ────────────────────────────────────────────────────────────

    def compress(
        self,
        history: list[dict],
        system_prompt: str,
        skill_guidance: str = "",
        turn_header: str = "",
    ) -> list[dict]:
        """Return ``[system_msg, user_msg]`` with compressed debate context.

        ``turn_header`` is injected as the very first line of the user message so
        the model is immediately reminded of the topic and assigned stances.
        """
        last_opp = self._last_opponent_message(history)
        summary = self._build_summary(history)
        angles = self._used_angles(history)

        parts: list[str] = []
        if turn_header:
            parts.append(turn_header)
        if summary:
            parts.append(f"DEBATE SO FAR:\n{summary}")
        if angles:
            bullet = "\n".join(f"- {a}" for a in angles)
            parts.append(f"ALREADY ARGUED — do NOT repeat:\n{bullet}")
        if last_opp:
            parts.append(f"OPPONENT'S LAST MESSAGE:\n{last_opp}")
        else:
            parts.append(
                "OPENING TURN — no opponent message yet. "
                "Begin directly with your strongest opening argument."
            )
        if skill_guidance:
            parts.append(skill_guidance.strip())

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": "\n\n".join(parts)},
        ]

    # ── private ───────────────────────────────────────────────────────────

    def _last_opponent_message(self, history: list[dict]) -> str:
        """Return the most recent non-empty user (opponent) message."""
        for entry in reversed(history):
            if entry.get("role") == "user" and entry.get("content", "").strip():
                return entry["content"].strip()
        return ""

    def _build_summary(self, history: list[dict]) -> str:
        """One-line snippet per turn, excluding the final entry (shown separately)."""
        turns = [
            e for e in history
            if e.get("role") in ("assistant", "user") and e.get("content", "").strip()
        ]
        # Exclude the last user entry — it's already rendered as OPPONENT'S LAST MESSAGE.
        if turns and turns[-1].get("role") == "user":
            turns = turns[:-1]
        if not turns:
            return ""
        snippets: list[str] = []
        for entry in turns[-self._max_turns:]:
            label = "You" if entry["role"] == "assistant" else "Opponent"
            raw = entry["content"].strip()[:self._snippet].replace("\n", " ")
            snippets.append(f"[{label}] {raw}…")
        return "\n".join(snippets)

    def _used_angles(self, history: list[dict]) -> list[str]:
        """First meaningful sentence from each of the debater's own turns."""
        angles: list[str] = []
        seen: set[str] = set()
        for entry in history:
            if entry.get("role") != "assistant":
                continue
            for chunk in entry.get("content", "").split("."):
                chunk = chunk.strip()
                if len(chunk) > 15:
                    key = chunk[:60].lower()
                    if key not in seen:
                        seen.add(key)
                        angles.append(chunk[:80])
                    break
        return angles
