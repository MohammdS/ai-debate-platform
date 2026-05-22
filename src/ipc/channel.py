import asyncio
import json

from src.ipc.message import DebateMessage


class IpcChannel:
    """
    Named, typed IPC channel backed by asyncio.Queue.

    Messages are serialized to JSON strings on the wire — not raw Python objects —
    to make the inter-process boundary explicit (simulates FIFO/socket behaviour).
    """

    def __init__(self, name: str, timeout: float = 120.0):
        self.name = name
        self.timeout = timeout
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, message: DebateMessage) -> None:
        """Serialize message to JSON and put it on the queue."""
        raw = json.dumps(message.to_dict())
        await self._queue.put(raw)

    async def receive(self) -> DebateMessage:
        """
        Block until a message arrives or timeout expires.
        Raises asyncio.TimeoutError on timeout — callers must handle it.
        """
        raw = await asyncio.wait_for(self._queue.get(), timeout=self.timeout)
        self._queue.task_done()
        return DebateMessage.from_dict(json.loads(raw))

    def __repr__(self) -> str:
        return f"IpcChannel(name={self.name!r}, qsize={self._queue.qsize()})"
