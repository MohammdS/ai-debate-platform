"""DebaterIpcMixin — IPC process-loop for the Debater agent.

Extracted from debater.py to keep each module under 150 physical lines.
The mixin requires its host class to have:
  - self.inbox / self.outbox  : IpcChannel instances
  - self.name                 : str
  - self.logger               : Logger
  - async self.get_argument() : the debate argument generator
"""
from __future__ import annotations

from src.ipc.message import DebateMessage, MessageType


class DebaterIpcMixin:
    """Adds the IPC process-loop to the Debater without coupling debate logic to IPC."""

    async def _process_relay(self, msg: DebateMessage, history: list[dict]) -> None:
        """Handle one RELAY message: generate an argument and send it back."""
        if msg.payload:
            history.append({"role": "user", "content": msg.payload})
        self.logger.info("[%s] generating argument for round %d", self.name, msg.round_num)
        argument = await self.get_argument(history, round_num=msg.round_num)
        history.append({"role": "assistant", "content": argument})
        sources = getattr(self, "last_sources", [])
        await self.outbox.send(DebateMessage(
            msg_type=MessageType.ARGUMENT, sender=self.name,
            receiver="judge", payload=argument, round_num=msg.round_num,
            metadata={"sources": sources} if sources else {},
        ))
        self.logger.info("[%s] sent ARGUMENT round %d", self.name, msg.round_num)

    async def run(self) -> None:
        """IPC process loop — blocks on inbox, responds to RELAY and SHUTDOWN."""
        if not (self.inbox and self.outbox):
            raise RuntimeError(f"{self.name}: channels must be set before run()")
        history: list[dict] = []
        self.logger.info("[%s] IPC process started", self.name)
        while True:
            try:
                msg = await self.inbox.receive()
            except TimeoutError:
                self.logger.warning("[%s] inbox timeout — exiting", self.name)
                break
            if msg.msg_type == MessageType.SHUTDOWN:
                self.logger.info("[%s] received SHUTDOWN — exiting", self.name)
                break
            if msg.msg_type == MessageType.RELAY:
                await self._process_relay(msg, history)
