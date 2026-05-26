from __future__ import annotations

import asyncio
import json
import logging
import time

from src.ipc.message import DebateMessage

logger = logging.getLogger(__name__)


class IpcChannel:
    """
    Named, typed IPC channel backed by asyncio.Queue.

    Messages are serialised to JSON on the wire (simulates FIFO/socket).
    When *validate* is True, every send() is checked against the protocol
    rules in src.ipc.protocol — ProtocolError is raised on violation.
    """

    def __init__(self, name: str, timeout: float = 120.0,
                 validate: bool = True) -> None:
        self.name = name
        self.timeout = timeout
        self.validate = validate
        self.last_activity: float = time.monotonic()
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: DebateMessage) -> None:
        """Validate (optional) then serialise and enqueue the message."""
        if self.validate:
            from src.ipc.protocol import validate_message
            validate_message(message)
        self.last_activity = time.monotonic()
        raw = json.dumps(message.to_dict())
        await self._queue.put(raw)
        logger.debug("[%s] sent %s→%s [%s] round=%d",
                     self.name, message.sender, message.receiver,
                     message.msg_type, message.round_num)

    async def receive(self) -> DebateMessage:
        """Block until a message arrives or *timeout* seconds elapse."""
        raw = await asyncio.wait_for(self._queue.get(), timeout=self.timeout)
        self._queue.task_done()
        self.last_activity = time.monotonic()
        msg = DebateMessage.from_dict(json.loads(raw))
        logger.debug("[%s] recv %s→%s [%s] round=%d",
                     self.name, msg.sender, msg.receiver,
                     msg.msg_type, msg.round_num)
        return msg

    def idle_seconds(self) -> float:
        """Seconds since last send or receive on this channel."""
        return time.monotonic() - self.last_activity

    def __repr__(self) -> str:
        return f"IpcChannel(name={self.name!r}, qsize={self._queue.qsize()})"
