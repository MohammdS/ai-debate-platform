from __future__ import annotations

from src.ipc.message import DebateMessage, MessageType


class JudgeRelayMixin:
    """Mixin providing _relay_round and _finalize for Judge."""

    async def _relay_round(self, rnd: int) -> bool:
        """Relay one A→B→A exchange. Returns False on timeout."""
        try:
            msg_a = await self.inbox_a.receive()
        except TimeoutError:
            self.logger.error("[judge] timeout on debater_a round %d", rnd)
            return False
        self.transcript.append({"role": "user", "name": "Debater_A", "content": msg_a.payload})
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
        self.transcript.append({"role": "user", "name": "Debater_B", "content": msg_b.payload})
        self.logger.info("[Debater B | Round %d]: %s", rnd, msg_b.payload)
        if self.event_queue:
            await self.event_queue.put({"type": "message", "message": self.transcript[-1],
                                        "count": len(self.transcript)})
        await self.outbox_a.send(DebateMessage(
            msg_type=MessageType.RELAY, sender="judge",
            receiver="debater_a", payload=msg_b.payload, round_num=rnd,
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
                verdict_text = f"Verdict unavailable — judge API error: {exc}"
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
