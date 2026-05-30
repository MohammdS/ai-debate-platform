from __future__ import annotations

from src.ipc.message import DebateMessage, MessageType


class JudgeRelayMixin:
    """Mixin providing _relay_round and _finalize for Judge."""

    @staticmethod
    def _fallback_winner(transcript: list[dict]) -> str:
        """
        Deterministic fallback winner selection when judge scoring fails.
        Uses total content length per side; ties resolve to Pro (Debater_A).
        """
        a_len = sum(len(e.get("content", "")) for e in transcript if e.get("name") == "Debater_A")
        b_len = sum(len(e.get("content", "")) for e in transcript if e.get("name") == "Debater_B")
        return "Pro" if a_len >= b_len else "Contra"

    async def _relay_round(self, rnd: int, is_final: bool = False) -> bool:
        """Relay one A→B exchange; relay B's response back to A unless this is the final round."""
        try:
            msg_a = await self.inbox_a.receive()
        except TimeoutError:
            self.logger.error("[judge] timeout on debater_a round %d", rnd)
            return False
        entry_a = {"role": "user", "name": "Debater_A", "content": msg_a.payload}
        if msg_a.metadata.get("sources"):
            entry_a["sources"] = msg_a.metadata["sources"]
        self.transcript.append(entry_a)
        self.logger.info("[Debater A | Round %d]: %s", rnd, msg_a.payload)
        if self.event_queue:
            await self.event_queue.put({"type": "message", "message": self.transcript[-1],
                                        "count": len(self.transcript)})
        await self.outbox_b.send(DebateMessage(
            msg_type=MessageType.RELAY, sender="judge",
            receiver="debater_b", payload=msg_a.payload, round_num=rnd,
        ))
        try:
            msg_b = await self.inbox_b.receive()
        except TimeoutError:
            self.logger.error("[judge] timeout on debater_b round %d", rnd)
            return False
        entry_b = {"role": "user", "name": "Debater_B", "content": msg_b.payload}
        if msg_b.metadata.get("sources"):
            entry_b["sources"] = msg_b.metadata["sources"]
        self.transcript.append(entry_b)
        self.logger.info("[Debater B | Round %d]: %s", rnd, msg_b.payload)
        if self.event_queue:
            await self.event_queue.put({"type": "message", "message": self.transcript[-1],
                                        "count": len(self.transcript)})
        if not is_final:
            await self.outbox_a.send(DebateMessage(
                msg_type=MessageType.RELAY, sender="judge",
                receiver="debater_a", payload=msg_b.payload, round_num=rnd + 1,
            ))
        return True

    async def _finalize(self, total_rounds: int) -> None:
        """Evaluate transcript (or emit debate_failed) then send VERDICT + SHUTDOWNs."""
        if not self._has_valid_entries(self.transcript):
            self.logger.error("[judge] transcript empty — debate failed")
            verdict_text = ("debate_failed: No debater arguments were recorded. "
                            "Check API keys and provider availability.")
        else:
            self.logger.info("[judge] evaluating transcript (%d entries)", len(self.transcript))
            if self.event_queue:
                await self.event_queue.put({"type": "judging"})
            try:
                verdict_text = await self.evaluate(self._truncate_transcript(self.transcript))
            except Exception as exc:
                self.logger.error("[judge] verdict API call failed: %s", exc)
                winner = self._fallback_winner(self.transcript)
                verdict_text = (
                    "SCORES\n"
                    "Pro   - Logic: 0/20 | Evidence: 0/20 | Rebuttal Quality: 0/20 | "
                    "Relevance: 0/10 | Clarity: 0/10 | Citation Quality: 0/10 | "
                    "Consistency: 0/10 | TOTAL: 0/100\n"
                    "Contra - Logic: 0/20 | Evidence: 0/20 | Rebuttal Quality: 0/20 | "
                    "Relevance: 0/10 | Clarity: 0/10 | Citation Quality: 0/10 | "
                    "Consistency: 0/10 | TOTAL: 0/100\n\n"
                    f"WINNER: {winner}\n"
                    "REASONING: Judge API evaluation failed; deterministic fallback was applied "
                    "to enforce non-tie assignment rules."
                )
        self.logger.info("[judge] VERDICT:\n%s", verdict_text)
        await self.verdict_channel.send(DebateMessage(
            msg_type=MessageType.VERDICT, sender="judge", receiver="orchestrator",
            payload=verdict_text, round_num=total_rounds))
        for outbox, recv in [(self.outbox_a, "debater_a"), (self.outbox_b, "debater_b")]:
            await outbox.send(DebateMessage(
                msg_type=MessageType.SHUTDOWN, sender="judge", receiver=recv,
                payload="", round_num=0))
        if self.event_queue:
            await self.event_queue.put({"type": "_done"})
