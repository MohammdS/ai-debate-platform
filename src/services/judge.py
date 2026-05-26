from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.ipc.message import DebateMessage, MessageType
from src.sdk.base_client import BaseAIClient
from src.services.base_agent import BaseAgent, enforce_word_limit, get_agent_prompt
from src.shared.config import ConfigManager
from src.shared.gatekeeper import ApiGatekeeper

if TYPE_CHECKING:
    from src.ipc.channel import IpcChannel

_cfg = ConfigManager()
_MAX_WORDS: int = _cfg.get_value("debate", "judge_max_words", 200)


class Judge(BaseAgent):
    """
    Impartial judge — acts as the central IPC relay hub (father process).
    All messages between debaters pass through the judge; no direct peer comms.
    """

    def __init__(self, client: BaseAIClient, gatekeeper: ApiGatekeeper):
        super().__init__("judge", client, gatekeeper)
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
        # Optional event queue — GUI streaming reads live events from here
        self.event_queue: asyncio.Queue | None = None
        # IPC channels — assigned by DebateOrchestrator before run()
        self.inbox_a:       IpcChannel | None = None  # receives from debater_a
        self.inbox_b:       IpcChannel | None = None  # receives from debater_b
        self.outbox_a:      IpcChannel | None = None  # sends to debater_a
        self.outbox_b:      IpcChannel | None = None  # sends to debater_b
        self.verdict_channel: IpcChannel | None = None  # sends verdict to orchestrator

    async def evaluate(self, transcript: list[dict]) -> str:
        """Direct SDK call — preserved for tests and backward compatibility."""
        formatted = "\n".join(
            f"[{e.get('name', 'Unknown')}]: {e.get('content', '')}"
            for e in transcript
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                f"The debate has ended. Here is the full transcript:\n\n{formatted}\n\n"
                "Issue your verdict now using the exact scoring format specified."
            )},
        ]
        response = await self.gatekeeper.execute(self.client.generate_response, messages)
        return enforce_word_limit(response, _MAX_WORDS, "judge", self.logger)

    async def run(self, total_rounds: int = 10) -> None:  # type: ignore[override]
        """
        IPC mediator loop.

        Each round:
          1. Receive ARGUMENT from debater_a via inbox_a
          2. Log + print, relay to debater_b via outbox_b
          3. Receive ARGUMENT from debater_b via inbox_b
          4. Log + print, relay to debater_a via outbox_a
        After all rounds: evaluate transcript, emit VERDICT, send SHUTDOWN.
        """
        assert all([self.inbox_a, self.inbox_b, self.outbox_a,
                    self.outbox_b, self.verdict_channel]), \
            "All channels must be set before judge.run()"

        self.logger.info("[judge] IPC mediator process started")

        try:
            for round_num in range(1, total_rounds + 1):
                # --- Phase 1: A → judge → B ---
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

                # --- Phase 2: B → judge → A ---
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

        finally:
            # Always send verdict and shutdown — even if a round timed out mid-debate
            self.logger.info("[judge] evaluating transcript (%d entries)", len(self.transcript))
            if self.event_queue:
                await self.event_queue.put({"type": "judging"})
            try:
                verdict_text = await self.evaluate(self.transcript)
            except Exception as exc:
                self.logger.error("[judge] verdict API call failed: %s", exc)
                verdict_text = f"Verdict unavailable — judge API error: {exc}"
            print(f"\n{'='*50}\nJUDGE VERDICT:\n{verdict_text}\n{'='*50}")

            await self.verdict_channel.send(DebateMessage(
                msg_type=MessageType.VERDICT, sender="judge", receiver="orchestrator",
                payload=verdict_text, round_num=total_rounds,
            ))

            for outbox in [self.outbox_a, self.outbox_b]:
                await outbox.send(DebateMessage(
                    msg_type=MessageType.SHUTDOWN, sender="judge",
                    receiver="debater", payload="", round_num=0,
                ))
            if self.event_queue:
                await self.event_queue.put({"type": "_done"})
