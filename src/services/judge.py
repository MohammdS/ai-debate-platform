from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from src.ipc.message import DebateMessage, MessageType
from src.sdk.base_client import BaseAIClient
from src.services.base_agent import BaseAgent, enforce_word_limit, get_agent_prompt
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper
from src.skills import JudgeEvaluationSkill, SkillContext, SkillSelector

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_cfg = ConfigManager()
_MAX_WORDS: int = _cfg.get_value("debate", "judge_max_words", 200)
# Maximum transcript entries sent to evaluate(); older middle entries are dropped
# to stay within typical LLM context windows while preserving opening + closing arguments.
_MAX_TRANSCRIPT_ENTRIES: int = _cfg.get_value("debate", "judge_max_transcript_entries", 20)

_VALID_SIDES = {"pro", "contra", "debater_a", "debater_b", "a", "b"}


class Judge(BaseAgent):
    """Impartial judge — central IPC relay hub (father process)."""

    def __init__(self, client: BaseAIClient, gatekeeper: ApiGatekeeper,
                 beat_fn: Callable[[], None] | None = None):
        super().__init__("judge", client, gatekeeper, role="judge")
        self.beat_fn = beat_fn  # called after each relay round to signal liveness
        judge_cfg = get_agent_prompt("judge")
        criteria = "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}"
            for k, v in judge_cfg.get("scoring_criteria", {}).items()
        )
        rules = "\n".join(f"- {r}" for r in judge_cfg.get("rules", []))
        self.system_prompt = (
            f"{judge_cfg.get('system', '')}\n\n"
            "At the end of the debate you issue a final verdict using EXACTLY this format:\n\n"
            f"{judge_cfg.get('verdict_format', '')}\n\n"
            f"RULES FOR SCORING:\n{criteria}\n{rules}"
        )
        self.transcript: list[dict] = []
        self.event_queue: asyncio.Queue | None = None
        self.inbox_a:       IpcChannel | None = None
        self.inbox_b:       IpcChannel | None = None
        self.outbox_a:      IpcChannel | None = None
        self.outbox_b:      IpcChannel | None = None
        self.verdict_channel: IpcChannel | None = None
        self._skill_selector = SkillSelector([JudgeEvaluationSkill()])

    def _truncate_transcript(self, transcript: list[dict]) -> list[dict]:
        """Keep head + tail of long transcripts to avoid overflowing context windows."""
        if len(transcript) <= _MAX_TRANSCRIPT_ENTRIES:
            return transcript
        head = 2  # always include opening arguments from both sides
        tail = _MAX_TRANSCRIPT_ENTRIES - head
        dropped = len(transcript) - _MAX_TRANSCRIPT_ENTRIES
        self.logger.warning(
            "[judge] transcript truncated: %d entries dropped (head=%d, tail=%d)",
            dropped, head, tail,
        )
        ellipsis_entry = {
            "role": "system",
            "name": "system",
            "content": f"[... {dropped} middle exchange(s) omitted for brevity ...]",
        }
        return transcript[:head] + [ellipsis_entry] + transcript[-tail:]

    def _build_judge_skill_guidance(self, transcript: list[dict]) -> str:
        ctx = SkillContext(
            topic="", stance="", opponent_last_message="", round_num=0,
            skill_type="judge", transcript=transcript,
        )
        results = self._skill_selector.select(ctx)
        parts = [r.content for r in results if r.selected and r.content]
        if not parts:
            return ""
        return "\n\nSKILL GUIDANCE:\n" + "\n".join(f"- {p}" for p in parts)

    async def generate(self, messages: list[dict]) -> str:
        """Call the LLM and return a validated, word-limited response."""
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        response = self._validate_response(response)
        return enforce_word_limit(response, _MAX_WORDS, "judge", self.logger)

    @staticmethod
    def _extract_winner(text: str) -> str | None:
        """Return the declared winner token after 'WINNER:' or None if absent."""
        lower = text.lower()
        idx = lower.find("winner:")
        if idx == -1:
            return None
        after = lower[idx + len("winner:"):].strip()
        token = after.split()[0].rstrip(".,;") if after.split() else ""
        return token if token in _VALID_SIDES else None

    async def evaluate(self, transcript: list[dict]) -> str:
        """Direct SDK call — preserved for tests and backward compatibility."""
        formatted = "\n".join(
            f"[{e.get('name', 'Unknown')}]: {e.get('content', '')}"
            for e in transcript
        )
        skill_guidance = self._build_judge_skill_guidance(transcript)
        user_text = (
            f"The debate has ended. Here is the full transcript:\n\n{formatted}\n\n"
            "Issue your verdict now using the exact scoring format specified."
            + skill_guidance
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_text},
        ]
        verdict = await self.generate(messages)
        if self._extract_winner(verdict) is None:
            raise ValueError("Judge must declare a winner")
        return verdict

    async def run(self, total_rounds: int = 10) -> None:  # type: ignore[override]
        """IPC mediator loop — relays A↔B, then evaluates and emits verdict."""
        if not all([self.inbox_a, self.inbox_b, self.outbox_a,
                    self.outbox_b, self.verdict_channel]):
            raise RuntimeError("All channels must be set before judge.run()")
        self.logger.info("[judge] IPC mediator process started")
        try:
            for round_num in range(1, total_rounds + 1):
                try:
                    msg_a = await self.inbox_a.receive()
                except TimeoutError:
                    self.logger.error(f"[judge] timeout on debater_a round {round_num}")
                    break
                self.transcript.append({"role": "user", "name": "Debater_A", "content": msg_a.payload})
                print(f"\n[Debater A | Round {round_num}]: {msg_a.payload}")
                self.logger.info(f"[judge] relaying A→B round {round_num}")
                if self.event_queue:
                    await self.event_queue.put({"type": "message",
                        "message": self.transcript[-1], "count": len(self.transcript)})
                await self.outbox_b.send(DebateMessage(
                    msg_type=MessageType.RELAY, sender="judge", receiver="debater_b",
                    payload=msg_a.payload, round_num=round_num,
                ))
                try:
                    msg_b = await self.inbox_b.receive()
                except TimeoutError:
                    self.logger.error(f"[judge] timeout on debater_b round {round_num}")
                    break
                self.transcript.append({"role": "user", "name": "Debater_B", "content": msg_b.payload})
                print(f"\n[Debater B | Round {round_num}]: {msg_b.payload}")
                self.logger.info(f"[judge] relaying B→A round {round_num}")
                if self.event_queue:
                    await self.event_queue.put({"type": "message",
                        "message": self.transcript[-1], "count": len(self.transcript)})
                await self.outbox_a.send(DebateMessage(
                    msg_type=MessageType.RELAY, sender="judge", receiver="debater_a",
                    payload=msg_b.payload, round_num=round_num,
                ))
                # Signal liveness to watchdog after each complete relay cycle
                if self.beat_fn:
                    self.beat_fn()
        finally:
            self.logger.info("[judge] evaluating transcript (%d entries)", len(self.transcript))
            if self.event_queue:
                await self.event_queue.put({"type": "judging"})
            try:
                verdict_text = await self.evaluate(self._truncate_transcript(self.transcript))
            except Exception as exc:
                self.logger.error("[judge] verdict API call failed: %s", exc)
                verdict_text = f"Verdict unavailable — judge API error: {exc}"
            print(f"\n{'='*50}\nJUDGE VERDICT:\n{verdict_text}\n{'='*50}")
            await self.verdict_channel.send(DebateMessage(
                msg_type=MessageType.VERDICT, sender="judge", receiver="orchestrator",
                payload=verdict_text, round_num=total_rounds,
            ))
            for outbox, receiver in [(self.outbox_a, "debater_a"), (self.outbox_b, "debater_b")]:
                await outbox.send(DebateMessage(
                    msg_type=MessageType.SHUTDOWN, sender="judge",
                    receiver=receiver, payload="", round_num=0,
                ))
            if self.event_queue:
                await self.event_queue.put({"type": "_done"})
