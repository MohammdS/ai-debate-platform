from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from src.sdk.base_client import BaseAIClient
from src.services.base_agent import BaseAgent, enforce_word_limit
from src.services.judge_prompts import (
    CLARIFY_PROMPT,
    MAX_TRANSCRIPT_ENTRIES,
    MAX_WORDS,
    WIN_RE,
    build_system_prompt,
    parse_structured_verdict,
)
from src.services.judge_relay import JudgeRelayMixin
from src.shared.gatekeeper import ApiGatekeeper
from src.skills import JudgeEvaluationSkill, SkillContext, SkillSelector

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_MAX_WORDS, _MAX_TRANSCRIPT_ENTRIES = MAX_WORDS, MAX_TRANSCRIPT_ENTRIES


class Judge(JudgeRelayMixin, BaseAgent):
    """Impartial judge — central IPC relay hub."""

    def __init__(self, client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 beat_fn: Callable[[], None] | None = None):
        super().__init__("judge", client, gatekeeper, role="judge")
        self.beat_fn = beat_fn
        self.system_prompt = build_system_prompt()
        self.transcript: list[dict] = []
        self.structured_verdict: dict | None = None
        self.event_queue: asyncio.Queue | None = None
        self.inbox_a = self.inbox_b = self.outbox_a = self.outbox_b = None
        self.verdict_channel: IpcChannel | None = None
        self._skill_selector = SkillSelector([JudgeEvaluationSkill()], debater_name="judge")

    def _truncate_transcript(self, t: list[dict]) -> list[dict]:
        if len(t) <= MAX_TRANSCRIPT_ENTRIES:
            return t
        head, tail = 2, MAX_TRANSCRIPT_ENTRIES - 2
        dropped = len(t) - MAX_TRANSCRIPT_ENTRIES
        self.logger.warning("[judge] transcript truncated: %d entries dropped", dropped)
        ellipsis = {"role": "system", "name": "system",
                    "content": f"[... {dropped} middle exchange(s) omitted ...]"}
        return t[:head] + [ellipsis] + t[-tail:]

    def _skill_guidance(self, transcript: list[dict]) -> str:
        ctx = SkillContext(topic="", stance="", opponent_last_message="",
                          round_num=0, skill_type="judge", transcript=transcript)
        parts = [r.content for r in self._skill_selector.select(ctx) if r.selected and r.content]
        return ("\n\nSKILL GUIDANCE:\n" + "\n".join(f"- {p}" for p in parts)) if parts else ""

    async def generate(self, messages: list[dict]) -> str:
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        return enforce_word_limit(self._validate_response(response), MAX_WORDS, "judge", self.logger)

    @staticmethod
    def _extract_winner(text: str) -> str | None:
        for pat in WIN_RE:
            m = pat.search(text)
            if m:
                return next(g for g in m.groups() if g).lower()
        return None

    @staticmethod
    def _has_valid_entries(transcript: list[dict]) -> bool:
        return any(e.get("content", "").strip() for e in transcript)

    async def evaluate(self, transcript: list[dict]) -> str:
        """Score the debate and declare a winner. Raises ValueError on bad transcript."""
        if not self._has_valid_entries(transcript):
            raise ValueError(
                "Cannot evaluate: transcript has no valid entries. "
                "API calls may have failed before any argument was recorded."
            )
        user_text = (
            "The debate has ended. Here is the full transcript:\n\n"
            + "\n".join(f"[{e.get('name','Unknown')}]: {e.get('content','')}" for e in transcript)
            + "\n\nIssue your verdict now using the exact scoring format specified."
            + self._skill_guidance(transcript)
        )
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user",   "content": user_text}]
        verdict = await self.generate(messages)
        if self._extract_winner(verdict) is None:
            self.logger.warning("[judge] WINNER missing — sending clarification prompt")
            clarification = await self.generate(
                messages + [{"role": "assistant", "content": verdict},
                             {"role": "user", "content": CLARIFY_PROMPT}]
            )
            verdict = verdict.rstrip() + "\n" + clarification
        if self._extract_winner(verdict) is None:
            raise ValueError("Judge must declare a winner")
        self.structured_verdict = parse_structured_verdict(verdict)
        _log = self.logger.info if self.structured_verdict else self.logger.warning
        _log("[judge] structured verdict %s", "parsed ok" if self.structured_verdict else "unparsed")
        return verdict

    async def run(self, total_rounds: int = 10) -> None:  # type: ignore[override]
        """Relay A↔B for total_rounds, then score and emit verdict."""
        if not all([self.inbox_a, self.inbox_b, self.outbox_a, self.outbox_b, self.verdict_channel]):
            raise RuntimeError("All channels must be set before judge.run()")
        self.logger.info("[judge] IPC mediator process started")
        try:
            for rnd in range(1, total_rounds + 1):
                if not await self._relay_round(rnd):
                    break
                if self.beat_fn:
                    self.beat_fn()
        finally:
            await self._finalize(total_rounds)
