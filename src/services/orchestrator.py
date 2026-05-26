import asyncio
from collections.abc import Callable

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType
from src.services.debater import Debater
from src.services.judge import Judge
from src.shared.config import ConfigManager
from src.shared.constants import MAX_ROUNDS
from src.shared.logger import setup_logger


class DebateOrchestrator:
    """
    Wires IPC channels and launches all three agent coroutines concurrently.

    Channel topology:
      a_to_judge : debater_a.outbox  → judge.inbox_a
      b_to_judge : debater_b.outbox  → judge.inbox_b
      judge_to_a : judge.outbox_a    → debater_a.inbox
      judge_to_b : judge.outbox_b    → debater_b.inbox
      verdict_ch : judge.verdict_channel → orchestrator reads
    """

    def __init__(self, debater_a: Debater, debater_b: Debater,
                 judge: Judge, rounds: int | None = None,
                 beat_fn: Callable[[], None] | None = None):
        self.debater_a = debater_a
        self.debater_b = debater_b
        self.judge = judge
        self.rounds = rounds if rounds is not None else ConfigManager().get_value("debate", "total_rounds", MAX_ROUNDS)
        self.history: list[dict] = []
        self.logger = setup_logger()
        if beat_fn:
            self.judge.beat_fn = beat_fn

    def _wire_channels(self, timeout: float = 120.0) -> IpcChannel:
        """Create all IPC channels and assign them to the three agents."""
        a_to_judge = IpcChannel("a_to_judge", timeout=timeout)
        b_to_judge = IpcChannel("b_to_judge", timeout=timeout)
        judge_to_a = IpcChannel("judge_to_a", timeout=timeout)
        judge_to_b = IpcChannel("judge_to_b", timeout=timeout)
        verdict_ch = IpcChannel("verdict",    timeout=timeout)

        self.debater_a.inbox  = judge_to_a
        self.debater_a.outbox = a_to_judge

        self.debater_b.inbox  = judge_to_b
        self.debater_b.outbox = b_to_judge

        self.judge.inbox_a        = a_to_judge
        self.judge.inbox_b        = b_to_judge
        self.judge.outbox_a       = judge_to_a
        self.judge.outbox_b       = judge_to_b
        self.judge.verdict_channel = verdict_ch

        return verdict_ch

    async def _seed_first_turn(self) -> None:
        """
        Bootstrap: send a synthetic RELAY to debater_a so the protocol
        can start. Without this, debater_a and the judge both block
        waiting for the other to speak first.
        """
        seed = DebateMessage(
            msg_type=MessageType.RELAY,
            sender="orchestrator",
            receiver="debater_a",
            payload=f"Begin the debate on: {self.debater_a.topic}",
            round_num=1,
        )
        await self.debater_a.inbox.send(seed)

    async def _run_judge_and_collect(self, verdict_ch: IpcChannel) -> str:
        """Runs the judge mediator loop, then reads the verdict off the channel.

        Ordering contract: judge.run() sends the VERDICT message to verdict_ch
        before returning, so the receive() below always finds a message already
        queued — there is no blocking wait beyond the channel timeout.
        """
        await self.judge.run(self.rounds)
        verdict_msg = await verdict_ch.receive()
        return verdict_msg.payload

    async def run_debate(self) -> str:
        """
        Wire channels, seed the first turn, then launch all three agent
        coroutines concurrently via asyncio.gather. Returns the final verdict.
        """
        self.logger.info("Starting IPC debate: %s", self.debater_a.topic)
        verdict_ch = self._wire_channels()
        await self._seed_first_turn()

        _, _, verdict = await asyncio.gather(
            self.debater_a.run(),
            self.debater_b.run(),
            self._run_judge_and_collect(verdict_ch),
        )

        self.history = self.judge.transcript
        return verdict
